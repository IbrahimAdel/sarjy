import json
from enum import StrEnum
from typing import Any, TypedDict


class ClientEvent(StrEnum):
    START = "start"
    STOP = "stop"
    USER_TRANSCRIPT = "user_transcript"


class ServerEvent(StrEnum):
    STATUS = "status"
    TRANSCRIPT_PARTIAL = "transcript_partial"
    TRANSCRIPT_FINAL = "transcript_final"
    TEXT_CHUNK = "text_chunk"
    ERROR = "error"


class AssistantState(StrEnum):
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    IDLE = "idle"


class StatusMessage(TypedDict):
    event: str
    state: str


class TranscriptMessage(TypedDict):
    event: str
    text: str


class ErrorMessage(TypedDict):
    event: str
    message: str


def status_message(state: AssistantState) -> StatusMessage:
    return {"event": ServerEvent.STATUS, "state": state}


def transcript_message(text: str, *, final: bool) -> TranscriptMessage:
    event = (
        ServerEvent.TRANSCRIPT_FINAL if final else ServerEvent.TRANSCRIPT_PARTIAL
    )
    return {"event": event, "text": text}


def error_message(message: str) -> ErrorMessage:
    return {"event": ServerEvent.ERROR, "message": message}


def parse_client_payload(raw: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
