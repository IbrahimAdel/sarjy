import asyncio
from typing import cast

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

import main
from services.voice.pipeline import AudioResult, VoiceSession
from services.voice.protocol import AssistantState
from services.voice.stt import SpeechToText
from services.voice.tts import NullTextToSpeech, TextToSpeech


class _FakeWebSocket:
    def __init__(self) -> None:
        self.json: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.json.append(payload)

    async def send_bytes(self, data: bytes) -> None:
        return None


class _ConfirmingVoice:
    """Reports a sustained (confirmed) utterance but no finished segment."""

    def __init__(self, **_kwargs) -> None:
        self.capturing = False

    def process_audio(self, _data: bytes) -> AudioResult:
        return AudioResult(speech_confirmed=True)

    def snapshot_pcm(self) -> bytes:
        return b""

    def reset(self) -> None:
        return None


class _UnavailableSTT:
    available = False


async def _pending() -> None:
    await asyncio.sleep(3600)


def _state(db_session: AsyncSession, status: AssistantState) -> main.ConnectionState:
    return main.ConnectionState(
        user_id="u1",
        conversation_id="c1",
        session=db_session,
        voice=cast(VoiceSession, _ConfirmingVoice()),
        status=status,
        speaking=status == AssistantState.SPEAKING,
    )


async def _run_turn(state: main.ConnectionState) -> _FakeWebSocket:
    websocket = _FakeWebSocket()
    await main._handle_audio(
        cast(WebSocket, websocket),
        state,
        cast(SpeechToText, _UnavailableSTT()),
        cast(TextToSpeech, NullTextToSpeech()),
        b"\x01" * 960,
        0.6,
        2.0,
    )
    return websocket


async def test_barge_in_is_ignored_while_thinking(db_session):
    state = _state(db_session, AssistantState.THINKING)
    task = asyncio.create_task(_pending())
    state.response_task = task
    try:
        websocket = await _run_turn(state)

        assert not task.done()
        assert state.status == AssistantState.THINKING
        assert websocket.json == []
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_barge_in_cancels_while_speaking(db_session):
    state = _state(db_session, AssistantState.SPEAKING)
    task = asyncio.create_task(_pending())
    state.response_task = task

    websocket = await _run_turn(state)

    assert task.cancelled()
    assert state.status == AssistantState.LISTENING
    assert {"event": "status", "state": "listening"} in websocket.json
