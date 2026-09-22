# Sarjy

A real-time, voice-first AI assistant: a browser client streams microphone
audio to a Python backend that transcribes speech, generates a reply with an
LLM, synthesizes spoken audio with local models, and streams text + audio back.

- **Frontend**: React + TypeScript + Vite (`frontend/`)
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite, local speech models (`backend/`)
- **Infra**: Docker Compose locally, Terraform for DigitalOcean App Platform (`terraform/`)

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs the backend's Python 3.12 automatically)
- Python 3.12 (managed by uv)
- Node.js 20+ and npm
- An OpenAI API key
- Optional: Docker + Docker Compose

---

## Option A — Quick start with Docker Compose

Runs the backend container (speech models baked in) and the frontend together.

```bash
# 1. Create the backend env file and set your OpenAI key
cp backend/.env.example backend/.env
# edit backend/.env -> OPENAI_API_KEY="sk-..."

# 2. Build and start
docker compose up --build
```

Open **http://localhost:8080**, register an account, and click **Start talking**.

Notes:

- The first backend build is slow and large: it downloads and bakes the
  Whisper (STT) and Piper/Kokoro (TTS) models into the image.
- Backend is exposed at http://localhost:8000; the frontend (port 8080) proxies
  API and WebSocket traffic to it.

---

## Option B — Run services manually (development)

### Backend

```bash
cd backend
cp .env.example .env          # then set OPENAI_API_KEY
uv sync                       # installs dependencies (and Python 3.12)
uv run alembic upgrade head   # create the SQLite schema
uv run uvicorn main:app --reload
```

The API runs at **http://localhost:8000** (docs at `/docs`).

Speech models are optional for local development:

- **STT** (faster-whisper) downloads `base.en` on first use.
- **TTS** needs a local voice file. Fetch the default Piper voice, or use Kokoro:
  ```bash
  uv run python -m piper.download_voices en_US-lessac-high --data-dir data/piper
  ```
- To run text-only (no mic/TTS), set `STT_ENABLED=false` and `TTS_ENABLED=false`
  in `backend/.env` and use the text input in the UI.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/auth`,
`/conversations`, `/ws`, etc. to the backend on port 8000 (no CORS setup needed).

---

## Using the app

1. Register or sign in.
2. Click **Start talking** and allow microphone access.
3. Speak — a live transcript appears, the assistant replies, and its audio plays.
4. You can also type a message in the input at the bottom.

---

## Common commands

Backend (run from `backend/`):

```bash
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # format
uv run basedpyright           # type check
```

Frontend (run from `frontend/`):

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Pre-commit hooks (backend ruff + basedpyright, cross-cutting hygiene) are
configured in `.pre-commit-config.yaml`. Install once with:

```bash
uv run --directory backend pre-commit install
```

---

## Configuration

- **Backend**: `backend/.env` (see `backend/.env.example`) covers the OpenAI key
  and model, the database URL, STT/TTS settings, VAD/endpointing, auth, CORS,
  and logging.
- **Frontend**: optional `VITE_API_URL` / `VITE_WS_URL` (`frontend/.env.example`).
  Leave them unset for same-origin/proxy behavior.
- **Auth** uses RS256 JWTs signed with the local dev key at
  `backend/auth/jwks.json`; replace it for any real deployment.
- **Database** defaults to SQLite at `backend/data/sarjy_memory.db`.

---

## Project layout

```
backend/     FastAPI app, voice pipeline, models, tests
frontend/    React app (voice client, conversations UI)
terraform/   DigitalOcean App Platform deployment
```

## Deployment

DigitalOcean App Platform is provisioned from `terraform/`. See the
architecture document for the deployment shape (backend Docker service +
frontend static site behind `/api` ingress).
