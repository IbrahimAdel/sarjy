import json
import logging
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from util import gen_uuid

LATENCY_STAGES = ("asr_ms", "llm_first_token_ms", "first_audio_ms", "total_ms")


class JsonFormatter(logging.Formatter):
    """Renders each record as a single JSON object with merged fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable line with trailing key=value fields."""

    def format(self, record: logging.LogRecord) -> str:
        line = (
            f"{self.formatTime(record, '%H:%M:%S')} "
            f"{record.levelname:<7} {record.name} {record.getMessage()}"
        )
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict) and fields:
            suffix = " ".join(f"{key}={value}" for key, value in fields.items())
            line = f"{line} {suffix}"
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def configure_logging(level: str = "INFO", log_format: str = "text") -> None:
    formatter: logging.Formatter
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = TextFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    logging.getLogger("sarjy").setLevel(level.upper())


@dataclass
class TurnMetrics:
    """Per-turn timestamps for deriving stage latencies."""

    user_id: str
    conversation_id: str
    turn_id: str = field(default_factory=gen_uuid)
    started_at: float = field(default_factory=time.perf_counter)
    _marks: dict[str, float] = field(default_factory=dict, repr=False)

    def mark(self, stage: str) -> None:
        self._marks.setdefault(stage, time.perf_counter())

    def _since_start_ms(self, stage: str) -> float | None:
        at = self._marks.get(stage)
        if at is None:
            return None
        return round((at - self.started_at) * 1000, 1)

    def _between_ms(self, start: str, end: str) -> float | None:
        first = self._marks.get(start)
        second = self._marks.get(end)
        if first is None or second is None:
            return None
        return round((second - first) * 1000, 1)

    def fields(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "asr_ms": self._between_ms("asr_start", "asr_end"),
            "llm_first_token_ms": self._between_ms(
                "llm_start", "llm_first_token"
            ),
            "first_audio_ms": self._since_start_ms("tts_first_audio"),
            "total_ms": self._since_start_ms("done"),
        }


class MetricsRegistry:
    """Thread-safe in-process aggregate of turn counters and stage latencies."""

    def __init__(self, max_samples: int = 1000) -> None:
        self._lock = threading.Lock()
        self._turns = 0
        self._cancelled = 0
        self._errors = 0
        self._stages: dict[str, deque[float]] = {
            stage: deque(maxlen=max_samples) for stage in LATENCY_STAGES
        }

    def record_turn(
        self,
        fields: dict[str, Any],
        *,
        cancelled: bool = False,
        error: bool = False,
    ) -> None:
        with self._lock:
            self._turns += 1
            if cancelled:
                self._cancelled += 1
            if error:
                self._errors += 1
            for stage in LATENCY_STAGES:
                value = fields.get(stage)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    self._stages[stage].append(float(value))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            latency: dict[str, dict[str, float]] = {}
            for stage, samples in self._stages.items():
                if samples:
                    latency[stage] = {
                        "count": len(samples),
                        "avg": round(sum(samples) / len(samples), 1),
                        "max": round(max(samples), 1),
                    }
            return {
                "turns": {
                    "total": self._turns,
                    "cancelled": self._cancelled,
                    "errors": self._errors,
                },
                "latency_ms": latency,
            }


metrics = MetricsRegistry()
