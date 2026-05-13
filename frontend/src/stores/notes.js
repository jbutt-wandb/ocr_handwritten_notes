import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sampleMarkdown, sampleImage, sampleFilename } from '../fixtures/testData'

const MAX_IMAGES = 5

export const useNotesStore = defineStore('notes', () => {
  const images = ref([])
  const options = ref({
    containsLatex: false,
    containsDiagrams: false
  })
  const customInstructions = ref('')
  const results = ref([])
  const isProcessing = ref(false)
  const currentImageIndex = ref(0)
  const error = ref(null)

  const combinedMarkdown = computed(() => {
    return results.value
      .map(r => r.markdown)
      .join('\n\n---\n\n')
  })

  async function addImages(files) {
    const remainingSlots = MAX_IMAGES - images.value.length
    const filesToAdd = files.slice(0, remainingSlots)

    const entries = await Promise.all(
      filesToAdd.map(file => new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => resolve({
          id: crypto.randomUUID(),
          file,
          preview: e.target.result,
          filename: file.name
        })
        reader.onerror = () => reject(reader.error)
        reader.readAsDataURL(file)
      }))
    )

    const available = MAX_IMAGES - images.value.length
    images.value.push(...entries.slice(0, available))

    return files.length > remainingSlots
  }

  function setImages(newOrder) {
    images.value = newOrder
  }

  function canAddMore() {
    return images.value.length < MAX_IMAGES
  }

  function getMaxImages() {
    return MAX_IMAGES
  }

  function removeImage(id) {
    images.value = images.value.filter(img => img.id !== id)
  }

  function clearImages() {
    images.value = []
  }

  function updateMarkdown(index, markdown) {
    if (results.value[index]) {
      results.value[index].markdown = markdown
    }
  }

  function setResults(newResults) {
    results.value = newResults
  }

  function setProcessing(value) {
    isProcessing.value = value
    if (!value) {
      currentImageIndex.value = 0
    }
  }

  function setCurrentImageIndex(index) {
    currentImageIndex.value = index
  }

  function setError(value) {
    error.value = value
  }

  function reset() {
    images.value = []
    results.value = []
    error.value = null
    options.value = {
      containsLatex: false,
      containsDiagrams: false
    }
    customInstructions.value = ''
  }

  function loadTestData() {
    results.value = [{
      filename: sampleFilename,
      markdown: sampleMarkdown,
      preview: sampleImage
    }]
  }

  return {
    images,
    options,
    customInstructions,
    results,
    isProcessing,
    currentImageIndex,
    error,
    combinedMarkdown,
    addImages,
    setImages,
    removeImage,
    clearImages,
    updateMarkdown,
    setResults,
    setProcessing,
    setCurrentImageIndex,
    setError,
    reset,
    canAddMore,
    getMaxImages,
    loadTestData
  }
})
