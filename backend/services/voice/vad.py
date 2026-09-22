from enum import StrEnum

import numpy as np
import webrtcvad

FRAME_DURATION_MS = (10, 20, 30)
SUPPORTED_SAMPLE_RATES = (8000, 16000, 32000, 48000)


class EndpointEvent(StrEnum):
    SPEECH_START = "speech_start"
    SPEECH_CONFIRMED = "speech_confirmed"
    SPEECH_END = "speech_end"


class FrameBuffer:
    """Splits a stream of raw PCM16 bytes into fixed-duration frames."""

    def __init__(self, sample_rate: int, frame_duration_ms: int = 30) -> None:
        if sample_rate not in SUPPORTED_SAMPLE_RATES:
            msg = f"Unsupported sample rate {sample_rate}; expected {SUPPORTED_SAMPLE_RATES}."
            raise ValueError(msg)
        if frame_duration_ms not in FRAME_DURATION_MS:
            msg = f"Unsupported frame duration {frame_duration_ms}ms; expected {FRAME_DURATION_MS}."
            raise ValueError(msg)

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_bytes = int(sample_rate * frame_duration_ms / 1000) * 2
        self._buffer = bytearray()

    def push(self, pcm: bytes) -> list[bytes]:
        self._buffer.extend(pcm)
        frames: list[bytes] = []
        while len(self._buffer) >= self.frame_bytes:
            frames.append(bytes(self._buffer[: self.frame_bytes]))
            del self._buffer[: self.frame_bytes]
        return frames

    def drain(self) -> bytes:
        remaining = bytes(self._buffer)
        self._buffer.clear()
        return remaining


def _frame_rms(pcm: bytes) -> float:
    samples = np.frombuffer(pcm, dtype=np.int16)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))


class VoiceActivityDetector:
    """Frame-level speech detection backed by WebRTC VAD."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2,
        min_energy: float = 0.0,
    ) -> None:
        if not 0 <= aggressiveness <= 3:
            msg = "aggressiveness must be between 0 and 3."
            raise ValueError(msg)

        self._frames = FrameBuffer(sample_rate, frame_duration_ms)
        self._vad = webrtcvad.Vad(aggressiveness)
        self._min_energy = max(0.0, min_energy)
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_bytes = self._frames.frame_bytes

    def push(self, pcm: bytes) -> list[tuple[bytes, bool]]:
        frames = self._frames.push(pcm)
        return [(frame, self._is_speech(frame)) for frame in frames]

    def _is_speech(self, frame: bytes) -> bool:
        if not self._vad.is_speech(frame, self.sample_rate):
            return False
        if self._min_energy > 0.0 and _frame_rms(frame) < self._min_energy:
            return False
        return True


class EndpointDetector:
    def __init__(
        self,
        frame_duration_ms: int = 30,
        min_speech_ms: int = 150,
        silence_ms: int = 700,
        max_speech_ms: int = 0,
        barge_in_min_speech_ms: int = 0,
    ) -> None:
        self.frame_duration_ms = frame_duration_ms
        self.min_speech_ms = min_speech_ms
        self.silence_ms = silence_ms
        self.max_speech_ms = max(0, max_speech_ms)
        self.barge_in_min_speech_ms = max(0, barge_in_min_speech_ms)
        self._speech_run_ms = 0
        self._silence_run_ms = 0
        self._speech_total_ms = 0
        self._in_speech = False
        self._confirmed = False

    @property
    def in_speech(self) -> bool:
        return self._in_speech

    def process(self, is_speech: bool) -> EndpointEvent | None:
        if not self._in_speech:
            if not is_speech:
                self._speech_run_ms = 0
                return None

            self._speech_run_ms += self.frame_duration_ms
            if self._speech_run_ms < self.min_speech_ms:
                return None

            self._in_speech = True
            self._silence_run_ms = 0
            self._speech_total_ms = self._speech_run_ms
            self._confirmed = False
            return EndpointEvent.SPEECH_START

        self._speech_total_ms += self.frame_duration_ms

        if is_speech:
            self._silence_run_ms = 0
        else:
            self._silence_run_ms += self.frame_duration_ms

        if self.max_speech_ms and self._speech_total_ms >= self.max_speech_ms:
            self._end()
            return EndpointEvent.SPEECH_END

        if self._silence_run_ms >= self.silence_ms:
            self._end()
            return EndpointEvent.SPEECH_END

        if (
            self.barge_in_min_speech_ms
            and not self._confirmed
            and self._speech_total_ms >= self.barge_in_min_speech_ms
        ):
            self._confirmed = True
            return EndpointEvent.SPEECH_CONFIRMED

        return None

    def _end(self) -> None:
        self._in_speech = False
        self._speech_run_ms = 0
        self._silence_run_ms = 0
        self._speech_total_ms = 0
        self._confirmed = False

    def reset(self) -> None:
        self._end()


def pre_roll_frames(
    frame_duration_ms: int, min_speech_ms: int, speech_pad_ms: int
) -> int:
    span = max(1, min_speech_ms + speech_pad_ms)
    return -(-span // frame_duration_ms)


__all__ = [
    "EndpointDetector",
    "EndpointEvent",
    "FrameBuffer",
    "VoiceActivityDetector",
    "pre_roll_frames",
]
