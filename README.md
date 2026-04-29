# Likho

**Turn photos of handwritten notes into clean, editable Markdown.**

*Likho (لِکھو) is Urdu for "write it."* Snap a picture of your notebook, drop it in, and Likho hands you back Markdown — equations, diagrams, and all — ready to paste into your tool of choice.

Built with Vue 3 + FastAPI, powered by [W&B Inference](https://docs.wandb.ai/guides/inference/) for vision OCR, with [Weave](https://weave-docs.wandb.ai/) tracing every call so you can see exactly what the model did.

## Features

- Drag and drop up to 5 images at once — they process in parallel
- Optional LaTeX equations and diagram descriptions
- Live Markdown editor with KaTeX math preview
- Pick your vision model from the gear icon — Kimi (default, fastest), Gemma, or Qwen
- First-run credentials modal — no manual `.env` editing required
- Every OCR call traced to your W&B project via Weave

## Prerequisites

- Python 3.11+ (we use [uv](https://docs.astral.sh/uv/) to manage it)
- Node.js 18+
- A W&B API key with Inference access — grab one at <https://wandb.ai/settings>

## Quick start

```bash
# Terminal 1 — backend
uv sync
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. On first launch a modal asks for your W&B API key, entity, and project. Paste them in, hit Save, and Likho writes them to a local `.env` file (gitignored, created if missing). You're ready to drop in an image.

## Configuration

Likho reads everything from a single `.env` file at the repo root. The in-app credentials modal (gear icon, top right) reads from and writes to this file — no restart needed.

```env
WANDB_API_KEY=          # required — powers W&B Inference and Weave tracing
ENTITY=                 # required — your W&B entity/team
PROJECT=                # required — your W&B project (Weave traces land here)
MODEL=                  # optional — defaults to moonshotai/Kimi-K2.5
```

Prefer to set things up by hand? Copy `.env.example` to `.env` and fill it in.

## Vision models

Pick whichever fits your page. Switch any time from the gear icon.

| Model | Notes |
| --- | --- |
| `moonshotai/Kimi-K2.5` *(default)* | Fastest. Great on clean, well-lit pages. |
| `google/gemma-4-31B-it` | More careful on dense or messy handwriting; slower. |
| `Qwen/Qwen3.5-35B-A3B` | Strong on structured layouts (tables, multi-column). |

All three are served by W&B Inference — see the [model catalog](https://docs.wandb.ai/guides/inference/) for the latest list.

## How it works

Likho calls W&B Inference's [OpenAI-compatible API](https://docs.wandb.ai/guides/inference/api-reference/) using the `openai` Python SDK. Images are downscaled to ≤1600px before sending (the API rejects very large base64 payloads), and structured output is enforced via `response_format={"type":"json_schema", ...}` so the model returns clean Markdown instead of prose-with-code-fences. Every OCR call is wrapped with `@weave.op`, so you'll find a full trace at `https://wandb.ai/<entity>/<project>/weave` after each run.

## Project layout

```
backend/
  main.py                 FastAPI app + Weave init
  routers/
    ocr.py                POST /api/v1/ocr/process
    config.py             GET/POST /api/v1/config
  services/
    inference_service.py  W&B Inference client + json_schema output + image resize
    credentials.py        Reads/writes .env via python-dotenv
  prompts/
    ocr_prompts.py        Prompt builder (LaTeX/diagram toggles)

frontend/src/
  views/                  UploadView, EditorView
  components/             CredentialsModal, DropZone, ImagePreview, ...
  stores/                 Pinia stores (notes, config, theme)
  services/api.js         HTTP client
```

## Troubleshooting

- **`wandb_not_configured` when uploading** — open the gear icon and fill in your W&B key, entity, and project.
- **Empty or truncated output** — some pages confuse one model and not another. Switch models from the gear icon and retry.
- **"Image too large" errors** — Likho already downscales to 1600px before sending. If you're hitting this on a smaller image, file an issue with the original.
- **Weave traces not showing up** — confirm `ENTITY` and `PROJECT` match a W&B project you have access to; the modal surfaces any init warnings.

## Learn more

- [W&B Inference docs](https://docs.wandb.ai/guides/inference/)
- [W&B Inference API reference](https://docs.wandb.ai/guides/inference/api-reference/)
- [Weave (LLM observability)](https://weave-docs.wandb.ai/)

## License

MIT — see `LICENSE` if added.
