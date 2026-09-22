import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro
from kokoro_onnx.config import SAMPLE_RATE as KOKORO_SAMPLE_RATE
from piper import PiperVoice

from settings import Settings

logger = logging.getLogger("sarjy.tts")


class TextToSpeech(ABC):
    """Text-to-speech backend (Piper or Kokoro, selected via configuration)."""

    @property
    def available(self) -> bool:
        return True

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError


class NullTextToSpeech(TextToSpeech):
    """Placeholder backend used when no voice model is configured."""

    @property
    def available(self) -> bool:
        return False

    @property
    def sample_rate(self) -> int:
        return 0

    async def synthesize(self, text: str) -> bytes:
        return b""


class PiperTextToSpeech(TextToSpeech):
    """Local neural TTS backed by Piper (ONNX Runtime)."""

    def __init__(self, voice: PiperVoice) -> None:
        self._voice = voice

    @property
    def sample_rate(self) -> int:
        return int(self._voice.config.sample_rate)

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            return b""
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        return b"".join(
            chunk.audio_int16_bytes for chunk in self._voice.synthesize(text)
        )


class KokoroTextToSpeech(TextToSpeech):
    """Local neural TTS backed by Kokoro (ONNX Runtime)."""

    def __init__(
        self,
        kokoro: Kokoro,
        *,
        voice: str,
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> None:
        self._kokoro = kokoro
        self._voice = voice
        self._speed = speed
        self._lang = lang

    @property
    def sample_rate(self) -> int:
        return int(KOKORO_SAMPLE_RATE)

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            return b""
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        samples, _ = self._kokoro.create(
            text,
            voice=self._voice,
            speed=self._speed,
            lang=self._lang,
        )
        pcm = np.clip(samples, -1.0, 1.0)
        return (pcm * 32767.0).astype(np.int16).tobytes()


def _load_piper(settings: Settings) -> TextToSpeech:
    if not settings.piper_voice_path:
        logger.info("TTS_PROVIDER=piper but PIPER_VOICE_PATH is unset; TTS disabled.")
        return NullTextToSpeech()

    path = Path(settings.piper_voice_path)
    if not path.exists():
        logger.info("Piper voice not found at %s; TTS disabled.", path)
        return NullTextToSpeech()

    try:
        voice = PiperVoice.load(path, use_cuda=settings.piper_use_cuda)
    except Exception:
        logger.exception("Failed to load Piper voice %r; TTS disabled.", path)
        return NullTextToSpeech()

    logger.info(
        "Loaded Piper voice %s (sample_rate=%d).",
        path.name,
        voice.config.sample_rate,
    )
    return PiperTextToSpeech(voice)


def _load_kokoro(settings: Settings) -> TextToSpeech:
    model_path = Path(settings.kokoro_model_path)
    voices_path = Path(settings.kokoro_voices_path)
    missing = [str(path) for path in (model_path, voices_path) if not path.exists()]
    if missing:
        logger.info("Kokoro files missing (%s); TTS disabled.", ", ".join(missing))
        return NullTextToSpeech()

    try:
        kokoro = Kokoro(str(model_path), str(voices_path))
    except Exception:
        logger.exception("Failed to load Kokoro model %r; TTS disabled.", model_path)
        return NullTextToSpeech()

    logger.info(
        "Loaded Kokoro voice %s (sample_rate=%d, speed=%.2f).",
        settings.kokoro_voice,
        KOKORO_SAMPLE_RATE,
        settings.kokoro_speed,
    )
    return KokoroTextToSpeech(
        kokoro,
        voice=settings.kokoro_voice,
        speed=settings.kokoro_speed,
        lang=settings.kokoro_lang,
    )


def load_text_to_speech(settings: Settings) -> TextToSpeech:
    if not settings.tts_enabled:
        logger.info("TTS disabled via configuration.")
        return NullTextToSpeech()

    provider = settings.tts_provider.strip().lower()
    if provider == "kokoro":
        return _load_kokoro(settings)
    if provider == "piper":
        return _load_piper(settings)

    logger.warning("Unknown TTS provider %r; TTS disabled.", settings.tts_provider)
    return NullTextToSpeech()
