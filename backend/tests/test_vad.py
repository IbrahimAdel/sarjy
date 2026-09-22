import pytest

from services.voice import pipeline
from services.voice.pipeline import VoiceSession
from services.voice.vad import (
    EndpointDetector,
    EndpointEvent,
    FrameBuffer,
    VoiceActivityDetector,
    pre_roll_frames,
)

FRAME_MS = 30


def test_frame_buffer_splits_into_fixed_frames():
    buffer = FrameBuffer(sample_rate=16000, frame_duration_ms=FRAME_MS)
    assert buffer.frame_bytes == 960

    frames = buffer.push(b"\x00" * 2000)
    assert len(frames) == 2
    assert all(len(frame) == 960 for frame in frames)
    assert len(buffer.drain()) == 80


def test_frame_buffer_rejects_bad_configuration():
    with pytest.raises(ValueError):
        FrameBuffer(sample_rate=12345)
    with pytest.raises(ValueError):
        FrameBuffer(sample_rate=16000, frame_duration_ms=25)


def test_vad_rejects_bad_aggressiveness():
    with pytest.raises(ValueError):
        VoiceActivityDetector(aggressiveness=5)


def test_pre_roll_covers_detection_window():
    assert pre_roll_frames(30, 150, 150) == 10


def test_endpoint_detector_emits_start_and_end():
    detector = EndpointDetector(
        frame_duration_ms=FRAME_MS, min_speech_ms=150, silence_ms=700
    )

    events = [detector.process(True) for _ in range(5)]
    assert events[:4] == [None, None, None, None]
    assert events[4] is EndpointEvent.SPEECH_START
    assert detector.in_speech

    end_events = [detector.process(False) for _ in range(24)]
    assert EndpointEvent.SPEECH_END not in end_events[:-1]
    assert end_events[-1] is EndpointEvent.SPEECH_END
    assert not detector.in_speech


def test_endpoint_detector_ignores_short_blips():
    detector = EndpointDetector(
        frame_duration_ms=FRAME_MS, min_speech_ms=150, silence_ms=700
    )
    assert all(detector.process(True) is None for _ in range(3))
    assert not detector.in_speech


def test_endpoint_detector_confirms_sustained_speech_once():
    detector = EndpointDetector(
        frame_duration_ms=FRAME_MS,
        min_speech_ms=150,
        silence_ms=700,
        barge_in_min_speech_ms=300,
    )

    events = [detector.process(True) for _ in range(10)]
    assert events[4] is EndpointEvent.SPEECH_START
    assert events.count(EndpointEvent.SPEECH_CONFIRMED) == 1
    assert events[-1] is EndpointEvent.SPEECH_CONFIRMED


def test_endpoint_detector_holds_barge_in_for_short_speech():
    detector = EndpointDetector(
        frame_duration_ms=FRAME_MS,
        min_speech_ms=150,
        silence_ms=700,
        barge_in_min_speech_ms=300,
    )
    # 6 frames = 180ms: started, but not yet sustained enough to interrupt.
    events = [detector.process(True) for _ in range(6)]
    assert EndpointEvent.SPEECH_CONFIRMED not in events


def test_endpoint_detector_forces_end_at_max_duration():
    detector = EndpointDetector(
        frame_duration_ms=FRAME_MS,
        min_speech_ms=150,
        silence_ms=10000,
        max_speech_ms=600,
    )

    end_frame = None
    for index in range(100):
        if detector.process(True) is EndpointEvent.SPEECH_END:
            end_frame = index
            break

    assert end_frame is not None
    assert end_frame < 30  # ended on the max-duration path, not the silence path
    assert not detector.in_speech


class _FakeVad:
    frame_bytes = 960

    def __init__(self, **kwargs) -> None:
        pass

    def push(self, pcm: bytes) -> list[tuple[bytes, bool]]:
        frame = b"\x00" * self.frame_bytes
        return [(frame, bool(pcm) and pcm[0] != 0)]


def test_voice_session_detects_speech_and_builds_segment(monkeypatch):
    monkeypatch.setattr(pipeline, "VoiceActivityDetector", _FakeVad)
    voice = VoiceSession(
        sample_rate=16000,
        frame_duration_ms=FRAME_MS,
        min_speech_ms=150,
        silence_ms=700,
    )

    started = False
    for _ in range(5):
        result = voice.process_audio(b"\x01" * 960)
        started = started or result.speech_started
    assert started
    assert voice.capturing
    assert len(voice.snapshot_pcm()) > 0

    segment = None
    for _ in range(24):
        result = voice.process_audio(b"\x00" * 960)
        if result.segment is not None:
            segment = result.segment
            break

    assert segment is not None
    assert segment.sample_rate == 16000
    assert segment.duration_ms > 0
    assert not voice.capturing


def test_voice_session_surfaces_barge_in_confirmation(monkeypatch):
    monkeypatch.setattr(pipeline, "VoiceActivityDetector", _FakeVad)
    voice = VoiceSession(
        sample_rate=16000,
        frame_duration_ms=FRAME_MS,
        min_speech_ms=150,
        silence_ms=700,
        barge_in_min_speech_ms=300,
    )

    confirmed = False
    for _ in range(10):
        result = voice.process_audio(b"\x01" * 960)
        confirmed = confirmed or result.speech_confirmed

    assert confirmed
