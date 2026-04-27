const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export async function processImages(images, options) {
  const formData = new FormData()

  images.forEach(img => {
    formData.append('images', img.file)
  })

  formData.append('contains_latex', options.containsLatex)
  formData.append('contains_diagrams', options.containsDiagrams)
  formData.append('custom_instructions', options.customInstructions || '')

  const response = await fetch(`${API_BASE}/ocr/process`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Processing failed')
  }

  return response.json()
}

export async function processSingleImage(image, options) {
  const formData = new FormData()
  formData.append('images', image.file)
  formData.append('contains_latex', options.containsLatex)
  formData.append('contains_diagrams', options.containsDiagrams)
  formData.append('custom_instructions', options.customInstructions || '')

  const response = await fetch(`${API_BASE}/ocr/process`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Processing failed')
  }

  return response.json()
}

export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`)
  return response.json()
}
