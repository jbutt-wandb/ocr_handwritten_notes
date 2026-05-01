# Likho

Turn photos of handwritten notes into editable Markdown. Vue 3 frontend, FastAPI backend, OpenAI Vision for OCR. Bring your own OpenAI API key.

## Features

- Drag-and-drop up to 5 images, processed in parallel
- LaTeX equations and diagram descriptions on demand
- Live Markdown editor with KaTeX preview
- In-app credentials modal — no `.env` required to get started

## Prerequisites

- Python 3.11+ (managed via [uv](https://docs.astral.sh/uv/))
- Node.js 18+
- An OpenAI API key with access to `gpt-4o`

## Quick start

```bash
# Backend
uv sync
uv run uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. On first run, a modal will prompt for your OpenAI API key. The key is stored locally in `.likho_config.json` (gitignored).

## Configuration

Credentials can be supplied two ways. The in-app modal takes precedence over the env file.

**Option A — in-app modal (recommended):** click the gear icon, paste your key, save.

**Option B — env file:** copy `.env.example` to `.env` and fill in values. The backend loads it on startup.

```env
OPENAI_API_KEY=sk-...
```

You can change the key at any time via the gear icon in the header.

## Project layout

```
backend/
  main.py             FastAPI app
  routers/
    ocr.py            POST /api/v1/ocr/process
    config.py         GET/POST /api/v1/config
  services/
    openai_service.py AsyncOpenAI + structured output
    credentials.py    Credential store (file > env precedence)
  prompts/
    ocr_prompts.py    Dynamic prompt builder

frontend/src/
  views/              UploadView, EditorView
  components/         CredentialsModal, DropZone, ImagePreview, ...
  stores/             Pinia stores (notes, config, theme)
  services/api.js     HTTP client
```

## Development notes

- The backend uses `AsyncOpenAI` so concurrent OCR requests truly run in parallel on a single uvicorn worker.
- OCR errors from OpenAI (auth, rate limit, model access) are surfaced verbatim to the upload screen.
- A built-in **Load Test Data** button (visible in dev) loads a sample image + OCR result without calling the API.

## License

MIT — see `LICENSE` if added.
