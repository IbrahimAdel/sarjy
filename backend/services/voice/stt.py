import asyncio
import logging
from abc import ABC, abstractmethod

from faster_whisper import WhisperModel

from services.voice.audio import pcm16_to_whisper_audio
from settings import Settings

logger = logging.getLogger("sarjy.stt")


class SpeechToText(ABC):
    """Speech-to-text backend."""

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    async def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        raise NotImplementedError


class NullSpeechToText(SpeechToText):
    """Placeholder backend used when no model is configured or loading fails."""

    @property
    def available(self) -> bool:
        return False

    async def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        return ""


class FasterWhisperSTT(SpeechToText):
    """Local speech-to-text backed by faster-whisper (CTranslate2)."""

    def __init__(
        self,
        model: WhisperModel,
        *,
        language: str = "en",
        beam_size: int = 1,
        no_speech_threshold: float = 0.6,
        log_prob_threshold: float = -1.0,
        vad_filter: bool = False,
    ) -> None:
        self._model = model
        self._language = language or None
        self._beam_size = beam_size
        self._no_speech_threshold = no_speech_threshold
        self._log_prob_threshold = log_prob_threshold
        self._vad_filter = vad_filter

    async def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        return await asyncio.to_thread(self._transcribe_sync, pcm, sample_rate)

    def _transcribe_sync(self, pcm: bytes, sample_rate: int) -> str:
        audio = pcm16_to_whisper_audio(pcm, sample_rate)
        if audio.size == 0:
            return ""

        segments, _ = self._model.transcribe(
            audio,
            language=self._language,
            beam_size=self._beam_size,
            temperature=0.0,
            condition_on_previous_text=False,
            without_timestamps=True,
            vad_filter=self._vad_filter,
            no_speech_threshold=self._no_speech_threshold,
        )

        parts: list[str] = []
        for segment in segments:
            # Drop segments the model itself considers silence or low-confidence
            # so background noise does not turn into a hallucinated response.
            if segment.no_speech_prob > self._no_speech_threshold:
                continue
            if segment.avg_logprob < self._log_prob_threshold:
                continue
            text = segment.text.strip()
            if text:
                parts.append(text)
        return " ".join(parts).strip()


def load_speech_to_text(settings: Settings) -> SpeechToText:
    if not settings.stt_enabled:
        logger.info("STT disabled via configuration.")
        return NullSpeechToText()

    try:
        model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    except Exception:
        logger.exception(
            "Failed to load faster-whisper model %r; voice input disabled.",
            settings.whisper_model,
        )
        return NullSpeechToText()

    logger.info(
        "Loaded faster-whisper model %r (device=%s, compute=%s).",
        settings.whisper_model,
        settings.whisper_device,
        settings.whisper_compute_type,
    )
    return FasterWhisperSTT(
        model,
        language=settings.whisper_language,
        no_speech_threshold=settings.whisper_no_speech_threshold,
        log_prob_threshold=settings.whisper_log_prob_threshold,
        vad_filter=settings.whisper_vad_filter,
    )
