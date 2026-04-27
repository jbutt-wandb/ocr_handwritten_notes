# OCR Notes App

Convert handwritten notes to editable markdown using AI-powered OCR.

## Features

- Upload multiple images of handwritten notes
- Support for LaTeX equations (rendered with KaTeX)
- Support for graphs and diagrams (described in text)
- Split-screen editor with live preview
- Dark/light mode toggle
- Download as markdown file

## Tech Stack

- **Backend**: FastAPI + OpenAI Vision API
- **Frontend**: Vue 3 + Tailwind CSS + Vite
- **LaTeX Rendering**: KaTeX

## Setup

### Prerequisites

- Python 3.14+
- Node.js 18+
- OpenAI API key

### Backend

```bash
# Install Python dependencies
uv sync

# Run the backend server
uv run uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The app will be available at `http://localhost:5173`

## Environment Variables

Create a `.env` file in the root directory:

```
OPENAI_API_KEY=your-api-key-here
```

## Usage

1. Start both the backend and frontend servers
2. Open `http://localhost:5173` in your browser
3. Upload images of your handwritten notes
4. Select options (LaTeX equations, diagrams) if applicable
5. Click "Process Notes" to run OCR
6. Edit the markdown in the split-screen editor
7. Download the final markdown file
