import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from piper import PiperVoice

from settings import Settings

logger = logging.getLogger("sarjy.tts")


class TextToSpeech(ABC):
    """Text-to-speech backend. Wired to Piper."""

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


def load_text_to_speech(settings: Settings) -> TextToSpeech:
    if not settings.tts_enabled:
        logger.info("TTS disabled via configuration.")
        return NullTextToSpeech()

    path = Path(settings.piper_voice_path) if settings.piper_voice_path else None
    if path is None or not path.exists():
        logger.info("No Piper voice configured; TTS disabled.")
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
