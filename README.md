# Likho

Turn photos of handwritten notes into editable Markdown. Vue 3 frontend, FastAPI backend. Pick the OCR provider you want — **OpenAI**, **Anthropic Claude**, or **Google Gemini** — and bring your own API key.

## Features

- Drag-and-drop up to 5 images, processed in parallel
- Choose your OCR provider per session: OpenAI `gpt-4o`, Claude `claude-sonnet-4-6`, or Gemini `gemini-2.5-pro`
- LaTeX equations and diagram descriptions on demand
- Live Markdown editor with KaTeX preview
- In-app credentials modal for all three providers — no `.env` required to get started

## Prerequisites

- Python 3.11+ (managed via [uv](https://docs.astral.sh/uv/))
- Node.js 18+
- At least one API key from a supported provider:
  - **OpenAI** — needs `gpt-4o` access
  - **Anthropic** — needs `claude-sonnet-4-6` access
  - **Google AI Studio** — needs `gemini-2.5-pro` access

## Quick start

### Option 1 — Docker (single command)

```bash
# Optional: pre-fill provider keys so the first run skips the modal
cp .env.example .env  # then edit and set at least one key

docker compose up --build
```

Open <http://localhost:5173>. The frontend is served by nginx (port 5173 → container 80) and the backend runs on <http://localhost:8000>.

Keys saved via the in-app modal persist in a named Docker volume (`likho_data`), so they survive `docker compose down`/`up`. Wipe with `docker compose down -v`. Updating `.env` requires `docker compose up --build` to take effect.

### Option 2 — Local dev

```bash
# Backend
uv sync
uv run uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

On first launch, a credentials modal appears. Pick your provider, paste its API key, and save. Keys are stored locally in `.likho_config.json` (gitignored).

## Using the app

1. **Pick a provider.** Click the gear icon in the header. The modal shows three providers (OpenAI / Claude / Gemini) with a checkmark next to whichever ones you've already configured. The radio button selects the active provider for the next OCR run.
2. **Add a key for the active provider.** Paste it into the input below the radio. Save. The masked, current value is shown after save (`sk-...abc from file`).
3. **Upload images.** Drag and drop up to 5 photos of handwritten notes onto the upload zone.
4. **Toggle options if needed.** "LaTeX equations" turns on math transcription; "Graphs & diagrams" emits descriptive blockquotes for figures; "Custom instructions" lets you steer the model further.
5. **Convert.** Click **Convert to Markdown**. The active provider is shown right under the button (e.g. _Using Claude_). If no key is set for the selected provider the button is disabled and a hint links to the gear icon.
6. **Edit.** Markdown opens in the editor with side-by-side preview (KaTeX-rendered math). Add more images mid-session via the "Add Image" button — they OCR with the same active provider.

Your provider choice persists in `localStorage` (key `likho.selectedProvider`), so reloading the page keeps the same active provider until you change it.

## Configuration

Credentials can be supplied two ways. The in-app modal takes precedence over the env file, per-field.

**Option A — in-app modal (recommended):** click the gear icon, pick a provider tab, paste the key, save. Repeat for any other provider you want available.

**Option B — env file:** copy `.env.example` to `.env` and fill in any subset of the three keys. Anything you don't set in `.env` can still be added later via the modal.

```env
# Each is optional, but at least one must be set to run OCR.
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

If both `.env` and the modal supply a key for the same provider, the modal wins (it writes to `.likho_config.json` which is loaded first).

## Project layout

```
backend/
  main.py                       FastAPI app
  routers/
    ocr.py                      POST /api/v1/ocr/process — dispatches by `provider` field
    config.py                   GET/POST /api/v1/config — per-provider credential status
  services/
    credentials.py              Credential store (file > env, per provider)
    providers/
      __init__.py               get_provider(name, store) factory
      base.py                   OCRProvider abstract + ProviderError envelope
      openai_provider.py        AsyncOpenAI + structured output
      anthropic_provider.py     AsyncAnthropic + tool-use for structured output
      gemini_provider.py        google-genai + responseSchema
  prompts/
    ocr_prompts.py              Dynamic prompt builder

frontend/src/
  views/                        UploadView, EditorView
  components/                   CredentialsModal (provider radio + conditional input), ...
  stores/                       Pinia stores (notes, config, theme)
  services/api.js               HTTP client; sends `provider` with each /ocr/process call
```

## How requests are routed

The frontend posts the active provider name with each OCR request:

```
POST /api/v1/ocr/process
images=...&provider=anthropic&contains_latex=false&...
```

The backend validates `provider`, looks up the matching API key from the credential store, and instantiates the corresponding `OCRProvider`. All three providers return a single `markdown` string via their respective structured-output mechanisms (`response_format` for OpenAI, tool use for Claude, `responseSchema` for Gemini).

If the selected provider has no key configured, the endpoint returns `503 provider_not_configured` and the UI surfaces a hint to add one.

## Development notes

- The backend runs each provider's async client (`AsyncOpenAI`, `AsyncAnthropic`, `google.genai` with `client.aio`) so multi-image fan-out is concurrent on a single uvicorn worker.
- Provider errors are normalized through a shared `ProviderError(status_code, code, message)` so the frontend always sees the same error envelope regardless of which SDK raised it.
- A built-in **Preview Editor** button (visible in dev) loads a sample image + OCR result without calling any API — handy for editor-only work.

## License

MIT — see `LICENSE` if added.
