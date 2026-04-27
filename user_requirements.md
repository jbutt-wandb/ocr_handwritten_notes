# OCR App: User Requirements

## Overview
Build an application that allows users to digitize their handwritten notes into editable markdown documents using AI-powered OCR.

## Tech Stack
- **Backend**: FastAPI (Python 3.14)
- **Frontend**: Vue 3 + Tailwind CSS + Vite
- **OCR Engine**: OpenAI Vision API (gpt-4o)
- **LaTeX Rendering**: KaTeX
- **State Management**: Pinia
- **Storage**: Browser localStorage (database to be added later)

---

## Screens

### 1. Upload Screen
Users land here first to upload their handwritten notes.

**Features:**
- Drag & drop zone for images (supports multiple files)
- File picker button as fallback
- Image thumbnails with remove option
- Form inputs:
  - Checkbox: "Contains LaTeX equations"
  - Checkbox: "Contains graphs/diagrams"
- "Process Notes" button to start OCR

**Behavior:**
- Accepts image files (jpg, jpeg, png, gif, webp)
- Shows loading spinner during OCR processing
- Navigates to Editor Screen on success

### 2. Editor Screen (Split-Screen View)
Users edit their OCR results here.

**Layout:**
- **Left panel (50%)**: Original images stacked vertically, scrollable
- **Right panel (50%)**: Markdown editor with sections per image, scrollable
- Both panels scroll independently

**Features:**
- Editable markdown text for each image
- Live LaTeX rendering with KaTeX (for equations like `$x^2$` and `$$\int f(x)dx$$`)
- "Download Markdown" button to export final document
- "Back" button to return to upload screen

---

## UI/UX Requirements

- **Theme**: Dark/light mode toggle, preference saved to localStorage
- **Design**: Clean, modern styling with Tailwind CSS
- **Feedback**: Loading spinners, error messages, success states
- **Responsive**: Works on desktop (mobile optimization optional for now)

---

## Backend API

### POST `/api/v1/ocr/process`

**Request**: `multipart/form-data`
- `images`: File[] (multiple image files)
- `contains_latex`: boolean
- `contains_diagrams`: boolean

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "image_index": 0,
      "filename": "page1.jpg",
      "markdown": "# Transcribed content..."
    }
  ]
}
```

---

## OCR Prompt Strategy

The OpenAI Vision prompt adapts based on user options:

| LaTeX | Diagrams | Prompt Behavior |
|-------|----------|-----------------|
| No | No | Basic text transcription with markdown formatting |
| Yes | No | + Convert equations to LaTeX ($inline$ and $$display$$) |
| No | Yes | + Describe diagrams/graphs in blockquotes |
| Yes | Yes | + Both LaTeX conversion and diagram descriptions |

---

## Technical Rules

1. Use OpenAI Vision API (gpt-4o model) for OCR processing
2. Environment variables stored in `.env` (OPENAI_API_KEY already configured)
3. Backend serves API only, frontend is a separate Vue SPA
4. CORS enabled for frontend dev server (localhost:5173)
5. No user authentication for now
6. No server-side persistence for now (localStorage only)

---

## Download Behavior

- Combines all markdown sections with `---` separators
- Downloads as `notes.md` file
- Plain text markdown (KaTeX renders on screen but exports as raw LaTeX syntax)
