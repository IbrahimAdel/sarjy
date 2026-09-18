from services.voice.protocol import (
    AssistantState,
    ServerEvent,
    error_message,
    parse_client_payload,
    status_message,
    transcript_message,
)


def test_parse_client_payload_valid():
    assert parse_client_payload('{"event": "start"}') == {"event": "start"}


def test_parse_client_payload_rejects_invalid_and_non_objects():
    assert parse_client_payload("not json") is None
    assert parse_client_payload("[1, 2, 3]") is None
    assert parse_client_payload('"a string"') is None


def test_message_builders():
    assert status_message(AssistantState.LISTENING) == {
        "event": ServerEvent.STATUS,
        "state": AssistantState.LISTENING,
    }
    assert transcript_message("hi", final=True) == {
        "event": ServerEvent.TRANSCRIPT_FINAL,
        "text": "hi",
    }
    assert transcript_message("hi", final=False) == {
        "event": ServerEvent.TRANSCRIPT_PARTIAL,
        "text": "hi",
    }
    assert error_message("boom") == {
        "event": ServerEvent.ERROR,
        "message": "boom",
    }
