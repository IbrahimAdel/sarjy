import numpy as np

from services.voice.audio import (
    float32_to_pcm16,
    iter_pcm_frames,
    pcm16_to_float32,
    pcm16_to_whisper_audio,
    resample_float32,
    resample_pcm16,
)


def test_pcm16_float32_round_trip():
    samples = np.array([0, 1000, -1000, 32767, -32768], dtype=np.int16)
    restored = float32_to_pcm16(pcm16_to_float32(samples.tobytes()))
    np.testing.assert_allclose(np.frombuffer(restored, dtype=np.int16), samples, atol=1)


def test_float32_to_pcm16_clips_out_of_range():
    samples = np.array([2.0, -2.0], dtype=np.float32)
    decoded = np.frombuffer(float32_to_pcm16(samples), dtype=np.int16)
    assert list(decoded) == [32767, -32767]


def test_resample_changes_length_proportionally():
    samples = np.sin(np.linspace(0, 10, 16000)).astype(np.float32)
    upsampled = resample_float32(samples, 16000, 48000)
    assert upsampled.size == 48000


def test_resample_same_rate_is_identity():
    samples = np.ones(100, dtype=np.float32)
    assert resample_float32(samples, 16000, 16000) is samples


def test_resample_pcm16_ratio():
    pcm = (np.zeros(8000, dtype=np.int16)).tobytes()
    upsampled = resample_pcm16(pcm, 16000, 48000)
    assert len(upsampled) == len(pcm) * 3


def test_pcm16_to_whisper_audio_always_16k():
    pcm = (np.zeros(48000, dtype=np.int16)).tobytes()
    assert pcm16_to_whisper_audio(pcm, 48000).size == 16000


def test_iter_pcm_frames_yields_expected_sizes():
    frames = list(iter_pcm_frames(b"\x00" * 10, 4))
    assert [len(frame) for frame in frames] == [4, 4, 2]
