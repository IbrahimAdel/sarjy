from collections import deque
from dataclasses import dataclass

from services.voice.vad import (
    EndpointDetector,
    EndpointEvent,
    VoiceActivityDetector,
    pre_roll_frames,
)


@dataclass(frozen=True)
class SpeechSegment:
    pcm: bytes
    sample_rate: int
    duration_ms: float


@dataclass(frozen=True)
class AudioResult:
    speech_started: bool = False
    segment: SpeechSegment | None = None


class VoiceSession:
    """Per-connection audio state: VAD framing, endpointing and buffering.

    Phase 1 only detects utterance boundaries. Speech-to-text and text-to-speech
    are injected in later phases.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        *,
        frame_duration_ms: int = 30,
        min_speech_ms: int = 150,
        silence_ms: int = 700,
        speech_pad_ms: int = 150,
        aggressiveness: int = 2,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self._vad = VoiceActivityDetector(
            sample_rate=sample_rate,
            frame_duration_ms=frame_duration_ms,
            aggressiveness=aggressiveness,
        )
        self._endpoint = EndpointDetector(
            frame_duration_ms=frame_duration_ms,
            min_speech_ms=min_speech_ms,
            silence_ms=silence_ms,
        )
        self._pre_roll: deque[bytes] = deque(
            maxlen=pre_roll_frames(frame_duration_ms, min_speech_ms, speech_pad_ms)
        )
        self._segment = bytearray()
        self._capturing = False

    @property
    def capturing(self) -> bool:
        return self._capturing

    @property
    def frame_bytes(self) -> int:
        return self._vad.frame_bytes

    def snapshot_pcm(self) -> bytes:
        """Current in-progress utterance audio, for partial transcription."""
        return bytes(self._segment)

    def process_audio(self, pcm: bytes) -> AudioResult:
        speech_started = False
        for frame, is_speech in self._vad.push(pcm):
            event = self._endpoint.process(is_speech)
            self._pre_roll.append(frame)

            if event is EndpointEvent.SPEECH_START:
                self._capturing = True
                self._segment = bytearray(b"".join(self._pre_roll))
                self._pre_roll.clear()
                speech_started = True
                continue

            if event is EndpointEvent.SPEECH_END:
                self._segment.extend(frame)
                return AudioResult(
                    speech_started=speech_started,
                    segment=self._finish_segment(),
                )

            if self._capturing:
                self._segment.extend(frame)

        return AudioResult(speech_started=speech_started)

    def _finish_segment(self) -> SpeechSegment:
        pcm = bytes(self._segment)
        self._capturing = False
        self._segment = bytearray()
        self._pre_roll.clear()
        duration_ms = (len(pcm) / 2) / self.sample_rate * 1000
        return SpeechSegment(
            pcm=pcm,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
        )

    def reset(self) -> None:
        self._endpoint.reset()
        self._pre_roll.clear()
        self._segment = bytearray()
        self._capturing = False
