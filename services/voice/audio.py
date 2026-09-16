from __future__ import annotations

from collections.abc import Iterator

import numpy as np

WHISPER_SAMPLE_RATE = 16000


def pcm16_to_float32(pcm: bytes) -> np.ndarray:
    """Convert signed 16-bit little-endian PCM to float32 in [-1, 1]."""
    if len(pcm) % 2:
        pcm = pcm[:-1]
    samples = np.frombuffer(pcm, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


def resample_float32(
    samples: np.ndarray, src_rate: int, dst_rate: int
) -> np.ndarray:
    """Linear-interpolation resampler, sufficient as STT model input."""
    if src_rate == dst_rate or samples.size == 0:
        return samples

    dst_len = round(samples.size * dst_rate / src_rate)
    if dst_len <= 0:
        return samples

    src_idx = np.linspace(0.0, samples.size - 1, num=dst_len)
    resampled = np.interp(src_idx, np.arange(samples.size), samples)
    return np.ascontiguousarray(resampled, dtype=np.float32)


def float32_to_pcm16(samples: np.ndarray) -> bytes:
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    samples = pcm16_to_float32(pcm)
    return float32_to_pcm16(resample_float32(samples, src_rate, dst_rate))


def iter_pcm_frames(pcm: bytes, frame_bytes: int) -> Iterator[bytes]:
    for start in range(0, len(pcm), frame_bytes):
        yield pcm[start : start + frame_bytes]


def pcm16_to_whisper_audio(pcm: bytes, sample_rate: int) -> np.ndarray:
    samples = pcm16_to_float32(pcm)
    return resample_float32(samples, sample_rate, WHISPER_SAMPLE_RATE)
