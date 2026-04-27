# OCR Handwritten Notes App - Implementation Plan

## Overview
Build an app to convert handwritten notes to editable markdown using OpenAI Vision API.

## Tech Stack
- **Backend**: FastAPI (Python 3.14)
- **Frontend**: Vue 3 + Tailwind CSS + Vite
- **OCR**: OpenAI Vision API (gpt-4o)
- **LaTeX Rendering**: KaTeX
- **State Management**: Pinia
- **Storage**: Browser localStorage (database later)

---

## Project Structure

```
ocr_app/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings & env vars
│   ├── routers/
│   │   └── ocr.py           # POST /api/v1/ocr/process endpoint
│   ├── services/
│   │   └── openai_service.py    # Vision API integration
│   └── prompts/
│       └── ocr_prompts.py   # Dynamic prompt templates
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── UploadView.vue   # Upload screen
│   │   │   └── EditorView.vue   # Split-screen editor
│   │   ├── components/
│   │   │   ├── DropZone.vue     # Drag & drop + file picker
│   │   │   ├── OptionsForm.vue  # LaTeX/diagram checkboxes
│   │   │   ├── ImagePanel.vue   # Left side - stacked images
│   │   │   ├── MarkdownEditor.vue  # Right side - editable markdown
│   │   │   └── ThemeToggle.vue  # Dark/light mode
│   │   ├── stores/
│   │   │   ├── notes.js     # Notes state (images, results)
│   │   │   └── theme.js     # Theme preference
│   │   └── services/
│   │       └── api.js       # Backend API client
│   └── package.json
├── pyproject.toml
└── .env                     # OPENAI_API_KEY (already configured)
```

---

## API Design

### POST `/api/v1/ocr/process`

**Request**: `multipart/form-data`
- `images`: File[] (multiple images)
- `contains_latex`: boolean
- `contains_diagrams`: boolean

**Response**:
```json
{
  "success": true,
  "results": [
    { "image_index": 0, "filename": "page1.jpg", "markdown": "..." }
  ]
}
```

---

## Key Features

### 1. Upload Screen
- Drag & drop zone + file picker button
- Image thumbnails with remove option
- Checkboxes: "Contains LaTeX equations", "Contains graphs/diagrams"
- "Process Notes" button

### 2. Editor Screen (Split-Screen)
- **Left panel**: Vertically stacked original images (scrollable)
- **Right panel**: Markdown editor sections per image (scrollable)
- Live KaTeX rendering for LaTeX equations
- "Download Markdown" button

### 3. UI/UX
- Dark/light mode toggle (persisted to localStorage)
- Clean, modern Tailwind styling
- Loading spinner during OCR processing
- Error handling with user-friendly messages

---

## OpenAI Vision Prompt Strategy

Build prompts dynamically based on user options:

| LaTeX | Diagrams | Prompt Components |
|-------|----------|-------------------|
| No | No | Base transcription instructions |
| Yes | No | + LaTeX formatting rules ($inline$ and $$display$$) |
| No | Yes | + Diagram description guidelines |
| Yes | Yes | + Both LaTeX and diagram instructions |

---

## Implementation Phases

### Phase 1: Backend Setup
1. Create FastAPI app structure with routers/services
2. Implement OpenAI Vision service with dynamic prompts
3. Create `/api/v1/ocr/process` endpoint
4. Add CORS for frontend dev server

### Phase 2: Frontend Setup
1. Initialize Vue 3 + Vite project
2. Configure Tailwind CSS with dark mode
3. Set up Vue Router (/ and /editor routes)
4. Create Pinia stores (notes, theme)

### Phase 3: Upload Screen
1. Build DropZone with drag & drop + file picker
2. Create image preview thumbnails
3. Build options form with checkboxes
4. Connect to backend API

### Phase 4: Editor Screen
1. Build split-screen layout (50/50)
2. Create ImagePanel with vertical scroll
3. Implement MarkdownEditor with per-section editing
4. Add KaTeX rendering for LaTeX preview
5. Implement markdown download

### Phase 5: Polish
1. Add ThemeToggle component
2. Loading states and error handling
3. Responsive design tweaks
4. End-to-end testing

---

## Dependencies

### Backend (pyproject.toml)
```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-multipart>=0.0.12
openai>=1.50.0
pydantic-settings>=2.5.0
```

### Frontend (package.json)
```
vue, vue-router, pinia
marked (markdown parsing)
katex (LaTeX rendering)
tailwindcss, vite, @vitejs/plugin-vue
```

---

## Critical Files to Implement

1. `backend/services/openai_service.py` - OpenAI Vision API integration
2. `backend/routers/ocr.py` - Image processing endpoint
3. `backend/prompts/ocr_prompts.py` - Dynamic prompt templates
4. `frontend/src/views/EditorView.vue` - Split-screen editor
5. `frontend/src/stores/notes.js` - Application state management
6. `frontend/src/components/DropZone.vue` - File upload component

---

## Verification

1. **Backend**: Run `uvicorn backend.main:app --reload`, test with curl/Postman
2. **Frontend**: Run `npm run dev`, verify UI renders correctly
3. **Integration**: Upload test images, verify OCR results appear in editor
4. **Download**: Edit markdown, download file, verify content is correct
5. **Theme**: Toggle dark/light mode, verify persistence after refresh
