from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")

    database_url: str = Field(default="sqlite:///./sarjy_memory.db")

    stt_enabled: bool = Field(default=True)
    whisper_model: str = Field(default="base.en")
    whisper_device: str = Field(default="cpu")
    whisper_compute_type: str = Field(default="int8")
    whisper_language: str = Field(default="en")
    partial_interval_ms: int = Field(default=600)

    tts_enabled: bool = Field(default=True)
    piper_voice_path: str = Field(default="")
    piper_use_cuda: bool = Field(default=False)

    sample_rate: int = Field(default=16000)

    log_level: str = Field(default="INFO")
    log_format: str = Field(default="text")

    def require_openai_api_key(self) -> str:
        if not self.openai_api_key.strip():
            msg = (
                "OPENAI_API_KEY is not set. Add it to your .env file "
                "(see .env.example) before starting Sarjy."
            )
            raise RuntimeError(msg)
        return self.openai_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
