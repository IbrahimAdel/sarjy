# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Builder: resolve dependencies into a venv and bake the Whisper model.
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    HF_HOME=/opt/hf

# libgomp1 is required by ctranslate2 (faster-whisper) to import the model.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Bake the faster-whisper model so the image can start without network access.
RUN --mount=type=cache,target=/root/.cache/uv \
    /app/.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8')"

# Bake the Piper voice model so TTS works without runtime downloads.
ARG PIPER_VOICE=en_US-lessac-high
RUN /app/.venv/bin/python -m piper.download_voices "${PIPER_VOICE}" --data-dir /opt/piper

# Bake the Kokoro voice models so TTS works without runtime downloads.
ARG KOKORO_MODEL_URL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
ARG KOKORO_VOICES_URL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
RUN /app/.venv/bin/python -c "import os, urllib.request as u; os.makedirs('/opt/kokoro', exist_ok=True); u.urlretrieve(os.environ['KOKORO_MODEL_URL'], '/opt/kokoro/kokoro-v1.0.onnx'); u.urlretrieve(os.environ['KOKORO_VOICES_URL'], '/opt/kokoro/voices-v1.0.bin')"

# ---------------------------------------------------------------------------
# Runtime: slim image with only the built venv, model cache and app source.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# libgomp1 is the only system library the native wheels need at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /opt/hf /opt/hf
COPY --from=builder /opt/piper /app/data/piper
COPY --from=builder /opt/kokoro /app/data/kokoro
COPY . .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ARG PIPER_VOICE=en_US-lessac-high

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf \
    DATABASE_URL="sqlite:///./data/sarjy_memory.db" \
    PIPER_VOICE_PATH="/app/data/piper/${PIPER_VOICE}.onnx"

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app /opt/hf
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/').status == 200 else 1)"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
