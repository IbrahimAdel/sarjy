from fastapi.testclient import TestClient

import main
from services.voice.pipeline import AudioResult, SpeechSegment


class FakeLLM:
    def __init__(self, user_id: str, conversation_id: str) -> None:
        pass

    async def generate_response_stream(self, session, user_transcript):
        yield "Hello "
        yield "world."


class FakeSTT:
    available = True

    async def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        return "fake transcript"


class FakeVoice:
    frame_bytes = 960

    def __init__(self, sample_rate: int = 16000, **kwargs) -> None:
        self.sample_rate = sample_rate
        self._capturing = False

    @property
    def capturing(self) -> bool:
        return self._capturing

    def snapshot_pcm(self) -> bytes:
        return b""

    def reset(self) -> None:
        self._capturing = False

    def process_audio(self, data: bytes) -> AudioResult:
        return AudioResult(
            speech_started=True,
            segment=SpeechSegment(
                pcm=data, sample_rate=self.sample_rate, duration_ms=100.0
            ),
        )


def _collect_until_idle(ws, limit: int = 100) -> list[dict]:
    messages: list[dict] = []
    for _ in range(limit):
        message = ws.receive_json()
        messages.append(message)
        if message.get("event") == "status" and message.get("state") == "idle":
            break
    return messages


def test_text_turn_streams_response(monkeypatch):
    monkeypatch.setattr(main, "LLMEngine", FakeLLM)

    with (
        TestClient(main.app) as client,
        client.websocket_connect("/ws/audio?user_id=u") as ws,
    ):
        assert ws.receive_json()["state"] == "listening"
        ws.send_json({"event": "user_transcript", "text": "hi"})
        messages = _collect_until_idle(ws)

    chunks = [m["text"] for m in messages if m.get("event") == "text_chunk"]
    assert chunks == ["Hello world."]
    states = [m["state"] for m in messages if m.get("event") == "status"]
    assert states[0] == "thinking"
    assert states[-1] == "idle"


def test_malformed_json_returns_error():
    with (
        TestClient(main.app) as client,
        client.websocket_connect("/ws/audio") as ws,
    ):
        ws.receive_json()
        ws.send_text("{not json")
        message = ws.receive_json()

    assert message["event"] == "error"
    assert "Malformed" in message["message"]


def test_unknown_event_returns_error():
    with (
        TestClient(main.app) as client,
        client.websocket_connect("/ws/audio") as ws,
    ):
        ws.receive_json()
        ws.send_json({"event": "bogus"})
        message = ws.receive_json()

    assert message["event"] == "error"


def test_empty_transcript_returns_error():
    with (
        TestClient(main.app) as client,
        client.websocket_connect("/ws/audio") as ws,
    ):
        ws.receive_json()
        ws.send_json({"event": "user_transcript", "text": "  "})
        message = ws.receive_json()

    assert message["event"] == "error"


def test_start_and_stop_statuses():
    with (
        TestClient(main.app) as client,
        client.websocket_connect("/ws/audio") as ws,
    ):
        ws.receive_json()
        ws.send_json({"event": "start"})
        assert ws.receive_json()["state"] == "listening"
        ws.send_json({"event": "stop"})
        assert ws.receive_json()["state"] == "idle"


def test_invalid_sample_rate_returns_error():
    with (
        TestClient(main.app) as client,
        client.websocket_connect("/ws/audio") as ws,
    ):
        ws.receive_json()
        ws.send_json({"event": "start", "sample_rate": 12345})
        message = ws.receive_json()

    assert message["event"] == "error"
    assert "sample_rate" in message["message"]


def test_audio_turn_transcribes_and_responds(monkeypatch):
    monkeypatch.setattr(main, "LLMEngine", FakeLLM)
    monkeypatch.setattr(main, "VoiceSession", FakeVoice)

    with TestClient(main.app) as client:
        main.app.state.stt = FakeSTT()
        with client.websocket_connect("/ws/audio?user_id=u") as ws:
            ws.receive_json()
            ws.send_bytes(b"\x01" * 960)
            messages = _collect_until_idle(ws)

    finals = [m["text"] for m in messages if m.get("event") == "transcript_final"]
    assert finals == ["fake transcript"]
    chunks = [m["text"] for m in messages if m.get("event") == "text_chunk"]
    assert chunks == ["Hello world."]
