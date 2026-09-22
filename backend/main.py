import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from auth import AuthError, authenticate, extract_token, load_public_jwks
from auth.router import router as auth_router
from conversations.router import router as conversations_router
from database import AsyncSessionLocal
from observability import TurnMetrics, configure_logging, metrics
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
    configure_logging(settings.log_level, settings.log_format)
    settings.require_openai_api_key()

    app.state.settings = settings
    app.state.stt = await asyncio.to_thread(load_speech_to_text, settings)
    app.state.tts = await asyncio.to_thread(load_text_to_speech, settings)
    logger.info(
        "startup_complete",
        extra={
            "fields": {
                "stt_available": app.state.stt.available,
                "tts_available": app.state.tts.available,
                "stt_model": settings.whisper_model,
                "log_format": settings.log_format,
            }
        },
    )
    yield
    logger.info("shutdown_complete")


app = FastAPI(title="Sarjy Voice Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(conversations_router)


@dataclass
class ConnectionState:
    user_id: str
    conversation_id: str
    session: AsyncSession
    voice: VoiceSession
    last_partial_at: float = field(default=0.0)
    speaking: bool = False
    status: AssistantState = AssistantState.LISTENING
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    response_task: asyncio.Task[None] | None = None
    partial_task: asyncio.Task[None] | None = None


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Sarjy API running"}


@app.get("/.well-known/jwks.json")
async def jwks_endpoint() -> dict[str, Any]:
    return load_public_jwks()


@app.get("/metrics")
async def metrics_endpoint() -> dict[str, Any]:
    return metrics.snapshot()


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


async def _set_status(
    websocket: WebSocket,
    state: ConnectionState,
    status: AssistantState,
    *,
    force: bool = False,
) -> None:
    """Track the assistant state and only notify the client on real changes."""
    if not force and state.status == status:
        return
    state.status = status
    await _send_json(websocket, state, status_message(status))


def _make_voice(sample_rate: int) -> VoiceSession:
    settings = get_settings()
    return VoiceSession(
        sample_rate=sample_rate,
        min_speech_ms=settings.vad_min_speech_ms,
        silence_ms=settings.vad_silence_ms,
        speech_pad_ms=settings.vad_speech_pad_ms,
        aggressiveness=settings.vad_aggressiveness,
        min_energy=settings.vad_min_energy,
        max_speech_ms=settings.max_utterance_ms,
        barge_in_min_speech_ms=settings.vad_barge_in_min_speech_ms,
    )


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


async def _cancel_partial(state: ConnectionState) -> None:
    task = state.partial_task
    state.partial_task = None
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.debug("Partial task raised during cancellation", exc_info=True)


async def _drain_partial(state: ConnectionState) -> None:
    """Wait for an in-flight partial so STT calls never overlap."""
    task = state.partial_task
    state.partial_task = None
    if task is None or task.done():
        return
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.debug("Partial task raised while draining", exc_info=True)


async def _stream_sentences(
    tokens: AsyncIterator[str],
    *,
    on_token: Callable[[str], Awaitable[None]] | None = None,
) -> AsyncIterator[str]:
    """Forward tokens (for live text) and yield sentence-sized chunks for TTS."""
    buffer = ""
    async for token in tokens:
        if on_token is not None:
            await on_token(token)
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
    turn: TurnMetrics,
) -> None:
    if not tts.available:
        return

    pcm = await tts.synthesize(text)
    if not pcm:
        return

    output_rate = state.voice.sample_rate
    if tts.sample_rate != output_rate:
        pcm = await asyncio.to_thread(resample_pcm16, pcm, tts.sample_rate, output_rate)

    if not state.speaking:
        state.speaking = True
        await _set_status(websocket, state, AssistantState.SPEAKING)

    turn.mark("tts_first_audio")
    frame_bytes = int(output_rate * OUT_FRAME_MS / 1000) * 2
    for frame in iter_pcm_frames(pcm, frame_bytes):
        await _send_bytes(websocket, state, frame)


async def _speak_sentences(
    websocket: WebSocket,
    state: ConnectionState,
    tts: TextToSpeech,
    queue: asyncio.Queue[str | None],
    turn: TurnMetrics,
) -> None:
    """Play queued sentences so TTS never blocks token streaming."""
    while True:
        sentence = await queue.get()
        if sentence is None:
            return
        await _speak(websocket, state, tts, sentence, turn)


async def _run_llm(
    websocket: WebSocket,
    state: ConnectionState,
    tts: TextToSpeech,
    transcript: str,
    turn: TurnMetrics,
) -> None:
    llm = LLMEngine(user_id=state.user_id, conversation_id=state.conversation_id)
    state.speaking = False
    await _set_status(websocket, state, AssistantState.THINKING)
    turn.mark("llm_start")
    logger.info(
        "llm_start",
        extra={
            "fields": {
                "turn_id": turn.turn_id,
                "conversation_id": state.conversation_id,
            }
        },
    )

    first_token = True

    async def _on_token(token: str) -> None:
        nonlocal first_token
        if first_token:
            turn.mark("llm_first_token")
            first_token = False
        await _send_json(
            websocket, state, {"event": ServerEvent.TEXT_CHUNK, "text": token}
        )

    tts_queue: asyncio.Queue[str | None] = asyncio.Queue()
    speaker_task = asyncio.create_task(
        _speak_sentences(websocket, state, tts, tts_queue, turn)
    )

    try:
        async for sentence in _stream_sentences(
            llm.generate_response_stream(
                session=state.session, user_transcript=transcript
            ),
            on_token=_on_token,
        ):
            tts_queue.put_nowait(sentence)
        tts_queue.put_nowait(None)
        await speaker_task
    except asyncio.CancelledError:
        speaker_task.cancel()
        try:
            await speaker_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.debug("Speaker task raised during cancellation", exc_info=True)
        turn.mark("done")
        fields = turn.fields()
        logger.info("turn_cancelled", extra={"fields": fields})
        metrics.record_turn(fields, cancelled=True)
        raise
    except Exception:
        speaker_task.cancel()
        try:
            await speaker_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.debug("Speaker task raised during error teardown", exc_info=True)
        turn.mark("done")
        fields = turn.fields()
        logger.exception("llm_generation_failed", extra={"fields": fields})
        metrics.record_turn(fields, error=True)
        await _send_json(
            websocket, state, error_message("Failed to generate a response.")
        )
    else:
        turn.mark("done")
        fields = turn.fields()
        logger.info("turn_complete", extra={"fields": fields})
        metrics.record_turn(fields)

    state.speaking = False
    await _set_status(websocket, state, AssistantState.IDLE)


async def _start_response(
    websocket: WebSocket,
    state: ConnectionState,
    tts: TextToSpeech,
    transcript: str,
    turn: TurnMetrics,
) -> None:
    await _cancel_partial(state)
    await _cancel_response(state)
    state.response_task = asyncio.create_task(
        _run_llm(websocket, state, tts, transcript, turn)
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
        turn = TurnMetrics(user_id=state.user_id, conversation_id=state.conversation_id)
        turn.mark("asr_end")
        await _start_response(websocket, state, tts, text, turn)

    elif event == ClientEvent.START:
        await _cancel_partial(state)
        await _cancel_response(state)
        state.speaking = False

        conversation_id = payload.get("conversation_id")
        if conversation_id:
            state.conversation_id = str(conversation_id)

        sample_rate = payload.get("sample_rate")
        if sample_rate is not None:
            try:
                state.voice = _make_voice(int(sample_rate))
            except (TypeError, ValueError) as exc:
                await _send_json(
                    websocket, state, error_message(f"Invalid sample_rate: {exc}")
                )
                return

        await _set_status(websocket, state, AssistantState.LISTENING, force=True)

    elif event == ClientEvent.STOP:
        await _cancel_partial(state)
        await _cancel_response(state)
        state.voice.reset()
        state.speaking = False
        await _set_status(websocket, state, AssistantState.IDLE, force=True)

    else:
        await _send_json(websocket, state, error_message(f"Unknown event: {event!r}"))


async def _maybe_send_partial(
    websocket: WebSocket,
    state: ConnectionState,
    stt: SpeechToText,
    partial_interval_s: float,
    partial_window_s: float,
) -> None:
    if not stt.available or not state.voice.capturing or state.speaking:
        return

    # One transcription at a time; never block the receive loop waiting for it.
    if state.partial_task is not None and not state.partial_task.done():
        return

    now = time.monotonic()
    if now - state.last_partial_at < partial_interval_s:
        return
    state.last_partial_at = now

    pcm = state.voice.snapshot_pcm()
    window_bytes = int(state.voice.sample_rate * partial_window_s) * 2
    if window_bytes > 0:
        pcm = pcm[-window_bytes:]
    if len(pcm) < MIN_PARTIAL_BYTES:
        return

    state.partial_task = asyncio.create_task(
        _transcribe_partial(websocket, state, stt, pcm)
    )


async def _transcribe_partial(
    websocket: WebSocket,
    state: ConnectionState,
    stt: SpeechToText,
    pcm: bytes,
) -> None:
    try:
        text = (await stt.transcribe(pcm, state.voice.sample_rate)).strip()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Partial transcription failed")
        return

    if text and state.voice.capturing:
        await _send_json(websocket, state, transcript_message(text, final=False))


async def _handle_audio(
    websocket: WebSocket,
    state: ConnectionState,
    stt: SpeechToText,
    tts: TextToSpeech,
    data: bytes,
    partial_interval_s: float,
    partial_window_s: float,
) -> None:
    result = state.voice.process_audio(data)

    if result.speech_started and state.status in (
        AssistantState.LISTENING,
        AssistantState.IDLE,
    ):
        await _set_status(websocket, state, AssistantState.LISTENING)

    # Barge-in only interrupts audible playback; during THINKING a stray
    # utterance must not cancel the turn before it can answer.
    if result.speech_confirmed and state.status == AssistantState.SPEAKING:
        if state.response_task is not None and not state.response_task.done():
            logger.info(
                "barge_in",
                extra={"fields": {"conversation_id": state.conversation_id}},
            )
        await _cancel_response(state)
        state.speaking = False
        await _set_status(websocket, state, AssistantState.LISTENING)

    if result.segment is None:
        await _maybe_send_partial(
            websocket, state, stt, partial_interval_s, partial_window_s
        )
        return

    state.last_partial_at = time.monotonic()
    # Serialise STT: an in-flight partial must finish before the final pass.
    await _drain_partial(state)

    if not stt.available:
        logger.info(
            "utterance_detected",
            extra={
                "fields": {
                    "duration_ms": round(result.segment.duration_ms, 1),
                    "stt_available": False,
                }
            },
        )
        return

    turn = TurnMetrics(user_id=state.user_id, conversation_id=state.conversation_id)
    logger.info(
        "utterance_detected",
        extra={
            "fields": {
                "turn_id": turn.turn_id,
                "duration_ms": round(result.segment.duration_ms, 1),
            }
        },
    )

    # Reflect activity while the (possibly slow) transcription runs.
    await _set_status(websocket, state, AssistantState.THINKING)

    turn.mark("asr_start")
    try:
        text = (
            await stt.transcribe(result.segment.pcm, result.segment.sample_rate)
        ).strip()
    except Exception:
        turn.mark("done")
        fields = turn.fields()
        logger.exception("transcription_failed", extra={"fields": fields})
        metrics.record_turn(fields, error=True)
        await _send_json(websocket, state, error_message("Failed to transcribe audio."))
        await _set_status(websocket, state, AssistantState.LISTENING)
        return
    turn.mark("asr_end")

    if not text:
        logger.info("transcript_empty", extra={"fields": {"turn_id": turn.turn_id}})
        await _set_status(websocket, state, AssistantState.LISTENING)
        return

    logger.info(
        "transcript_ready",
        extra={"fields": {"turn_id": turn.turn_id, "chars": len(text)}},
    )
    await _send_json(websocket, state, transcript_message(text, final=True))
    await _start_response(websocket, state, tts, text, turn)


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    token = extract_token(websocket)
    if token is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized"
        )
        return

    try:
        user_id = authenticate(token)
    except AuthError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized"
        )
        return

    settings = app.state.settings
    stt: SpeechToText = app.state.stt
    tts: TextToSpeech = app.state.tts
    partial_interval_s = settings.partial_interval_ms / 1000
    partial_window_s = settings.partial_window_ms / 1000

    state = ConnectionState(
        user_id=user_id,
        conversation_id=websocket.query_params.get("conversation_id") or gen_uuid(),
        session=AsyncSessionLocal(),
        voice=_make_voice(settings.sample_rate),
    )
    logger.info(
        "connection_open",
        extra={
            "fields": {
                "user_id": state.user_id,
                "conversation_id": state.conversation_id,
            }
        },
    )

    await _set_status(websocket, state, AssistantState.LISTENING, force=True)

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            text = message.get("text")
            data = message.get("bytes")
            if text is not None:
                assert isinstance(text, str)
                await _handle_text(websocket, state, tts, text)
            elif data is not None:
                assert isinstance(data, bytes)
                await _handle_audio(
                    websocket,
                    state,
                    stt,
                    tts,
                    data,
                    partial_interval_s,
                    partial_window_s,
                )
    except WebSocketDisconnect:
        logger.info("connection_closed", extra={"fields": {"user_id": state.user_id}})
    finally:
        await _cancel_partial(state)
        await _cancel_response(state)
        await state.session.close()
