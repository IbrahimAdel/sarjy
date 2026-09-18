import json
import logging

from observability import (
    JsonFormatter,
    MetricsRegistry,
    TextFormatter,
    TurnMetrics,
)


def test_turn_metrics_computes_stage_latencies():
    turn = TurnMetrics(user_id="u", conversation_id="c")
    for stage in (
        "asr_start",
        "asr_end",
        "llm_start",
        "llm_first_token",
        "tts_first_audio",
        "done",
    ):
        turn.mark(stage)

    fields = turn.fields()
    assert fields["user_id"] == "u"
    assert fields["conversation_id"] == "c"
    for key in ("asr_ms", "llm_first_token_ms", "first_audio_ms", "total_ms"):
        assert fields[key] is not None, key


def test_turn_metrics_missing_stages_are_none():
    fields = TurnMetrics(user_id="u", conversation_id="c").fields()
    assert fields["asr_ms"] is None
    assert fields["first_audio_ms"] is None


def test_mark_is_idempotent():
    turn = TurnMetrics(user_id="u", conversation_id="c")
    turn.mark("asr_start")
    first = turn._marks["asr_start"]
    turn.mark("asr_start")
    assert turn._marks["asr_start"] == first


def test_metrics_registry_aggregates():
    registry = MetricsRegistry()
    fields = {"asr_ms": 100.0, "llm_first_token_ms": 50.0, "total_ms": 200.0}
    registry.record_turn(fields)
    registry.record_turn({"total_ms": 400.0}, cancelled=True)
    registry.record_turn({"total_ms": 300.0}, error=True)

    snapshot = registry.snapshot()
    assert snapshot["turns"] == {"total": 3, "cancelled": 1, "errors": 1}
    assert snapshot["latency_ms"]["total_ms"] == {
        "count": 3,
        "avg": 300.0,
        "max": 400.0,
    }
    assert snapshot["latency_ms"]["asr_ms"]["count"] == 1


def _record() -> logging.LogRecord:
    record = logging.LogRecord(
        "sarjy", logging.INFO, __file__, 1, "turn_complete", None, None
    )
    record.fields = {"total_ms": 123.4, "turn_id": "abc"}  # type: ignore[attr-defined]
    return record


def test_json_formatter_merges_fields():
    payload = json.loads(JsonFormatter().format(_record()))
    assert payload["event"] == "turn_complete"
    assert payload["logger"] == "sarjy"
    assert payload["total_ms"] == 123.4
    assert payload["turn_id"] == "abc"


def test_text_formatter_appends_fields():
    line = TextFormatter().format(_record())
    assert "turn_complete" in line
    assert "total_ms=123.4" in line
