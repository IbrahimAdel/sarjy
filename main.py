import asyncio
import logging
import time
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database import SessionLocal
from services.llm_service import LLMEngine
from services.voice.audio import iter_pcm_frames, resample_pcm16
from services.voice.pipeline import VoiceSession
from services.voice.protocol import (
    AssistantState,
    ClientEvent,
    ServerEvent,
    error_message,
    parse_client_payload,
    status_message,
    transcript_message,
)
from services.voice.stt import SpeechToText, load_speech_to_text
from services.voice.tts import TextToSpeech, load_text_to_speech
from settings import get_settings
from util import gen_uuid

logger = logging.getLogger("sarjy")

SENTENCE_ENDINGS = (".", "?", "!")
MIN_SENTENCE_CHARS = 12
MIN_PARTIAL_BYTES = 16000  # ~0.5s of 16 kHz PCM16 before partials are useful
OUT_FRAME_MS = 20


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.require_openai_api_key()

    app.state.settings = settings
    app.state.stt = await asyncio.to_thread(load_speech_to_text, settings)
    app.state.tts = await asyncio.to_thread(load_text_to_speech, settings)
    logger.info(
        "Sarjy started (stt_available=%s, tts_available=%s)",
        app.state.stt.available,
        app.state.tts.available,
    )
    yield
    logger.info("Sarjy shutting down")


app = FastAPI(title="Sarjy Voice Assistant", lifespan=lifespan)


@dataclass
class ConnectionState:
    user_id: str
    conversation_id: str
    session: Session
    voice: VoiceSession
    last_partial_at: float = field(default=0.0)
    speaking: bool = False
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    response_task: asyncio.Task[None] | None = None


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Sarjy API running"}


async def _send_json(
    websocket: WebSocket, state: ConnectionState, payload: Mapping[str, Any]
) -> None:
    async with state.send_lock:
        await websocket.send_json(payload)


async def _send_bytes(
    websocket: WebSocket, state: ConnectionState, data: bytes
) -> None:
    async with state.send_lock:
        await websocket.send_bytes(data)


async def _cancel_response(state: ConnectionState) -> None:
    task = state.response_task
    state.response_task = None
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.debug("Response task raised during cancellation", exc_info=True)


async def _stream_sentences(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
    buffer = ""
    async for token in tokens:
        buffer += token
        if len(buffer) >= MIN_SENTENCE_CHARS and buffer.rstrip().endswith(
            SENTENCE_ENDINGS
        ):
            yield buffer
            buffer = ""
    if buffer.strip():
        yield buffer


async def _speak(
    websocket: WebSocket,
    state: ConnectionState,
    tts: TextToSpeech,
    text: str,
) -> None:
    if not tts.available:
        return

    pcm = await tts.synthesize(text)
    if not pcm:
        return

    output_rate = state.voice.sample_rate
    if tts.sample_rate != output_rate:
        pcm = await asyncio.to_thread(
            resample_pcm16, pcm, tts.sample_rate, output_rate
        )

    if not state.speaking:
        state.speaking = True
        await _send_json(websocket, state, status_message(AssistantState.SPEAKING))

    frame_bytes = int(output_rate * OUT_FRAME_MS / 1000) * 2
    for frame in iter_pcm_frames(pcm, frame_bytes):
        await _send_bytes(websocket, state, frame)


async def _run_llm(
    websocket: WebSocket,
    state: ConnectionState,
    tts: TextToSpeech,
    transcript: str,
) -> None:
    llm = LLMEngine(user_id=state.user_id, conversation_id=state.conversation_id)
    state.speaking = False
    await _send_json(websocket, state, status_message(AssistantState.THINKING))
    try:
        tokens = llm.generate_response_stream(
            session=state.session, user_transcript=transcript
        )
        async for sentence in _stream_sentences(tokens):
            await _send_json(
                websocket,
                state,
                {"event": ServerEvent.TEXT_CHUNK, "text": sentence},
            )
            await _speak(websocket, state, tts, sentence)
    except asyncio.CancelledError:
        logger.info("Response cancelled (barge-in)")
        raise
    except Exception:
        logger.exception("LLM generation failed")
        await _send_json(
            websocket, state, error_message("Failed to generate a response.")
        )

    state.speaking = False
    await _send_json(websocket, state, status_message(AssistantState.IDLE))


async def _start_response(
    websocket: WebSocket,
    state: ConnectionState,
    tts: TextToSpeech,
    transcript: str,
) -> None:
    await _cancel_response(state)
    state.response_task = asyncio.create_task(
        _run_llm(websocket, state, tts, transcript)
    )


async def _handle_text(
    websocket: WebSocket,
    state: ConnectionState,
    tts: TextToSpeech,
    raw: str,
) -> None:
    payload = parse_client_payload(raw)
    if payload is None:
        await _send_json(websocket, state, error_message("Malformed JSON payload."))
        return

    event = payload.get("event")

    if event == ClientEvent.USER_TRANSCRIPT:
        text = str(payload.get("text", "")).strip()
        if not text:
            await _send_json(websocket, state, error_message("Empty transcript."))
            return
        await _start_response(websocket, state, tts, text)

    elif event == ClientEvent.START:
        await _cancel_response(state)
        state.speaking = False

        user_id = payload.get("user_id")
        if user_id:
            state.user_id = str(user_id)

        conversation_id = payload.get("conversation_id")
        if conversation_id:
            state.conversation_id = str(conversation_id)

        sample_rate = payload.get("sample_rate")
        if sample_rate is not None:
            try:
                state.voice = VoiceSession(sample_rate=int(sample_rate))
            except (TypeError, ValueError) as exc:
                await _send_json(
                    websocket, state, error_message(f"Invalid sample_rate: {exc}")
                )
                return

        await _send_json(websocket, state, status_message(AssistantState.LISTENING))

    elif event == ClientEvent.STOP:
        await _cancel_response(state)
        state.voice.reset()
        state.speaking = False
        await _send_json(websocket, state, status_message(AssistantState.IDLE))

    else:
        await _send_json(websocket, state, error_message(f"Unknown event: {event!r}"))


async def _maybe_send_partial(
    websocket: WebSocket,
    state: ConnectionState,
    stt: SpeechToText,
    partial_interval_s: float,
) -> None:
    if not stt.available or not state.voice.capturing:
        return

    now = time.monotonic()
    if now - state.last_partial_at < partial_interval_s:
        return
    state.last_partial_at = now

    pcm = state.voice.snapshot_pcm()
    if len(pcm) < MIN_PARTIAL_BYTES:
        return

    try:
        text = (await stt.transcribe(pcm, state.voice.sample_rate)).strip()
    except Exception:
        logger.exception("Partial transcription failed")
        return

    if text:
        await _send_json(websocket, state, transcript_message(text, final=False))


async def _handle_audio(
    websocket: WebSocket,
    state: ConnectionState,
    stt: SpeechToText,
    tts: TextToSpeech,
    data: bytes,
    partial_interval_s: float,
) -> None:
    result = state.voice.process_audio(data)

    if result.speech_started:
        await _cancel_response(state)
        state.speaking = False
        await _send_json(websocket, state, status_message(AssistantState.LISTENING))

    if result.segment is None:
        await _maybe_send_partial(websocket, state, stt, partial_interval_s)
        return

    state.last_partial_at = time.monotonic()

    if not stt.available:
        logger.info(
            "Detected utterance (%.0f ms) but no STT backend is configured.",
            result.segment.duration_ms,
        )
        return

    try:
        text = (await stt.transcribe(result.segment.pcm, result.segment.sample_rate)).strip()
    except Exception:
        logger.exception("Transcription failed")
        await _send_json(
            websocket, state, error_message("Failed to transcribe audio.")
        )
        await _send_json(websocket, state, status_message(AssistantState.LISTENING))
        return

    if not text:
        await _send_json(websocket, state, status_message(AssistantState.LISTENING))
        return

    await _send_json(websocket, state, transcript_message(text, final=True))
    await _start_response(websocket, state, tts, text)


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    settings = app.state.settings
    stt: SpeechToText = app.state.stt
    tts: TextToSpeech = app.state.tts
    partial_interval_s = settings.partial_interval_ms / 1000

    state = ConnectionState(
        user_id=websocket.query_params.get("user_id", "default_user"),
        conversation_id=websocket.query_params.get("conversation_id") or gen_uuid(),
        session=SessionLocal(),
        voice=VoiceSession(sample_rate=settings.sample_rate),
    )

    await _send_json(websocket, state, status_message(AssistantState.LISTENING))

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            text = message.get("text")
            data = message.get("bytes")
            if text is not None:
                await _handle_text(websocket, state, tts, text)
            elif data is not None:
                await _handle_audio(
                    websocket, state, stt, tts, data, partial_interval_s
                )
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        await _cancel_response(state)
        state.session.close()
