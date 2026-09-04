# Likho

Turn photos of handwritten notes into editable Markdown. Vue 3 frontend, FastAPI backend. Pick the OCR provider you want — **OpenAI**, **Anthropic Claude**, **Google Gemini**, **Mistral**, or a **local model server** (Ollama, LM Studio, vLLM) — and bring your own API key (or none at all for local).

## Features

- Drag-and-drop up to 5 images, processed in parallel (drag thumbnails to reorder before converting)
- Choose your OCR provider per session: OpenAI `gpt-4o`, Claude `claude-sonnet-4-6`, Gemini `gemini-2.5-flash`, Mistral `mistral-medium-latest`, or any model on a local OpenAI-compatible server
- LaTeX equations and diagram descriptions on demand, plus free-form custom instructions
- Per-image stacked editor with sticky source-image thumbnails, a full-screen lightbox, and live KaTeX-rendered Markdown preview
- **Add Diagrams** — crop regions out of a source page and embed them inline in the Markdown (fully client-side)
- Prompt-injection guardrail on the custom-instructions field (blocks malicious instructions before any provider call)
- In-app credentials modal with a provider dropdown — no `.env` required to get started
- Editorial light theme (serif type, no external services)

## Prerequisites

- Python 3.11+ (managed via [uv](https://docs.astral.sh/uv/))
- Node.js 18+
- At least one API key from a supported provider, or a running local model server:
  - **OpenAI** — needs `gpt-4o` access
  - **Anthropic** — needs `claude-sonnet-4-6` access
  - **Google AI Studio** — needs `gemini-2.5-flash` access
  - **Mistral** — a key from [console.mistral.ai](https://console.mistral.ai) with `mistral-medium-latest` access
  - **Local server** — Ollama, LM Studio, vLLM, or anything OpenAI-compatible, serving a vision-capable model (no key needed)

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

> **First run note:** the prompt-injection guardrail lazily downloads a small Hugging Face model the first time non-empty custom instructions are submitted. That one-time download adds a few seconds; subsequent runs are instant.

On first launch, a credentials modal appears. Pick your provider, paste its API key, and save. Keys are stored locally in `.likho_config.json` (gitignored).

## Using the app

1. **Pick a provider.** Click the gear icon in the header. The modal has a **provider dropdown** (OpenAI / Claude / Gemini / Mistral / Local server) with a ✓ next to whichever ones you've already configured. The selected provider becomes the active one for the next OCR run.
2. **Add a key for the active provider.** Paste it into the input below the dropdown and Save. The masked current value is shown after save (`sk-...abc from file`).
3. **Upload images.** Drag and drop up to 5 photos of handwritten notes. Drag the ⠿ handle on a thumbnail to reorder them; the order carries into the editor.
4. **Toggle options if needed.** "LaTeX equations" turns on math transcription; "Graphs & diagrams" emits descriptive blockquotes for figures; "Custom instructions" lets you steer the model further.
5. **Convert.** Click **Convert to markdown**. The active provider is shown under the button (e.g. _Using Claude · change_). If no key is set for the selected provider the button is disabled and a hint links to the gear icon.
6. **Edit.** Each image gets its own section — a sticky source thumbnail on the left (click to open a full-screen lightbox) and its Markdown on the right, with a synced Editor/Preview toggle (KaTeX-rendered math). Add more images mid-session via **Add Image** — they OCR with the same active provider.
7. **Embed diagrams (optional).** Click **Add Diagrams**, draw a rectangle over any figure on a source page, and it's inserted at your cursor as a `![label|W](crop:c_xxxx)` ref that renders inline in Preview.
8. **Download.** Click **Download** for a local `.md` file. Cropped diagrams are inlined as data URLs. Nothing is sent to any external service.

Your provider choice persists in `localStorage` (key `likho.selectedProvider`), so reloading the page keeps the same active provider until you change it.

## Configuration

Credentials can be supplied two ways. The in-app modal takes precedence over the env file, per-field.

**Option A — in-app modal (recommended):** click the gear icon, pick a provider from the dropdown, paste the key, save. Repeat for any other provider you want available.

**Option B — env file:** copy `.env.example` to `.env` and fill in any subset of the keys. Anything you don't set in `.env` can still be added later via the modal.

```env
# Each is optional, but at least one provider must be configured to run OCR.
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
MISTRAL_API_KEY=...
LOCAL_BASE_URL=http://localhost:11434/v1
LOCAL_MODEL=llama3.2-vision
LOCAL_API_KEY=          # only if your server enforces auth (e.g. vLLM --api-key)
```

If both `.env` and the modal supply a key for the same provider, the modal wins (it writes to `.likho_config.json` which is loaded first).

### Local models

Pick **Local server** in the credentials modal to run OCR against any OpenAI-compatible server on your machine — no cloud key required. The base URL defaults to Ollama (`http://localhost:11434/v1`); LM Studio is `http://localhost:1234/v1`, vLLM is wherever you bound it. The modal fetches the server's model list automatically (doubling as a connection test) — pick a **vision-capable** model, e.g.:

```bash
ollama pull llama3.2-vision   # or qwen2.5vl
```

Text-only models will produce empty or nonsense output. Local inference is slower than the cloud providers — the backend allows up to 5 minutes per image.

**Docker note:** from inside the backend container, `localhost` is the container itself. Use `http://host.docker.internal:11434/v1` to reach a server running on your host (the compose file already maps `host.docker.internal` on Linux).

## Project layout

```
backend/
  main.py                       FastAPI app
  routers/
    ocr.py                      POST /api/v1/ocr/process — guardrail + dispatch by `provider`
    config.py                   GET/POST /api/v1/config — per-provider credential status
  services/
    credentials.py              Credential store (file > env, per provider)
    guardrail.py                Prompt-injection scanner (llm_guard), process-wide singleton
    providers/
      __init__.py               get_provider(name, store) factory + SUPPORTED_PROVIDERS
      base.py                   OCRProvider abstract + ProviderError envelope
      openai_provider.py        AsyncOpenAI + structured output
      anthropic_provider.py     AsyncAnthropic + tool-use for structured output
      gemini_provider.py        google-genai + responseSchema
      mistral_provider.py       mistralai vision chat + clean_markdown
      local_provider.py         AsyncOpenAI against a user-configured base_url
  prompts/
    ocr_prompts.py              Dynamic prompt builder

frontend/src/
  views/                        UploadView, EditorView
  components/                   CredentialsModal (provider dropdown + conditional input),
                                DropZone, CropModal, ImagePreview, ...
  stores/                       Pinia stores (notes, config)
  services/api.js               HTTP client; sends `provider` with each /ocr/process call
```

## How requests are routed

The frontend posts the active provider name with each OCR request:

```
POST /api/v1/ocr/process
images=...&provider=mistral&contains_latex=false&custom_instructions=...
```

The backend first runs the **prompt-injection guardrail** on `custom_instructions` (empty → skipped; detected → `400 prompt_injection_detected`; scanner error → fails open). It then validates `provider`, looks up the matching API key from the credential store, and instantiates the corresponding `OCRProvider`. Each provider returns a single `markdown` string (via `response_format` for OpenAI, tool use for Claude, `responseSchema` for Gemini, and a plain vision-chat response cleaned of code fences for Mistral and local servers).

If the selected provider has no key configured, the endpoint returns `503 provider_not_configured` and the UI surfaces a hint to add one.

## Development notes

- The backend runs each provider's async client (`AsyncOpenAI`, `AsyncAnthropic`, `google.genai` with `client.aio`, `mistralai` with `complete_async`) so multi-image fan-out is concurrent on a single uvicorn worker.
- Provider errors are normalized through a shared `ProviderError(status_code, code, message)` so the frontend always sees the same error envelope regardless of which SDK raised it.
- Adding a provider is a one-entry-per-list change: a new `*_provider.py`, plus `SUPPORTED_PROVIDERS`/factory (`providers/__init__.py`), the credential fields (`credentials.py`, `config.py`, `routers/config.py`), and the frontend `SUPPORTED_PROVIDERS`/`PROVIDER_LABELS` (`stores/config.js`).
- Image cropping is entirely client-side: crops live in the notes store keyed by id, and `resolveCropsForPreview` / `resolveCropsForDownload` turn `crop:` refs into rendered `<img>` / inlined data URLs.
- A built-in **preview** button (visible in dev) loads a sample image + OCR result without calling any API — handy for editor-only work like cropping.

## License

MIT — see `LICENSE` if added.
