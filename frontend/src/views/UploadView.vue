<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotesStore } from '../stores/notes'
import { processSingleImage } from '../services/api'
import DropZone from '../components/DropZone.vue'
import ImagePreview from '../components/ImagePreview.vue'

const router = useRouter()
const notesStore = useNotesStore()
const showNoImagesMessage = ref(false)
const customInstructions = ref('')
const showCustomInstructions = ref(false)
const isDev = import.meta.env.DEV

function handleFilesSelected(files) {
  notesStore.addImages(files)
  showNoImagesMessage.value = false
}

function handleRemoveImage(id) {
  notesStore.removeImage(id)
}

async function handleSubmit() {
  if (notesStore.images.length === 0) {
    showNoImagesMessage.value = true
    return
  }

  console.log('=== Starting OCR Processing ===')
  console.log(`Processing ${notesStore.images.length} image(s)`)
  console.log(`Options: LaTeX=${notesStore.options.containsLatex}, Diagrams=${notesStore.options.containsDiagrams}`)
  if (customInstructions.value) {
    console.log(`Custom instructions: ${customInstructions.value.substring(0, 100)}...`)
  }

  notesStore.setProcessing(true)
  notesStore.setError(null)

  const options = {
    ...notesStore.options,
    customInstructions: customInstructions.value
  }

  const allResults = []

  try {
    for (let i = 0; i < notesStore.images.length; i++) {
      const image = notesStore.images[i]
      notesStore.setCurrentImageIndex(i + 1)
      console.log(`Processing image ${i + 1} of ${notesStore.images.length}: ${image.filename}`)

      const response = await processSingleImage(image, options)

      if (response.success && response.results.length > 0) {
        allResults.push({
          ...response.results[0],
          preview: image.preview
        })
      } else {
        throw new Error(response.error || `Failed to process image ${i + 1}`)
      }
    }

    console.log(`Processing complete. Processed ${allResults.length} images.`)
    notesStore.setResults(allResults)
    router.push('/editor')
  } catch (err) {
    console.error('Error during processing:', err)
    notesStore.setError(err.message || 'An unexpected error occurred')
  } finally {
    notesStore.setProcessing(false)
    console.log('=== Processing Finished ===')
  }
}

function loadTestData() {
  notesStore.loadTestData()
  router.push('/editor')
}
</script>

<template>
  <div>
    <!-- Processing Overlay -->
    <div
      v-if="notesStore.isProcessing"
      style="position: fixed; inset: 0; background-color: rgba(0, 0, 0, 0.75); display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 9999;"
    >
      <svg style="width: 48px; height: 48px; color: var(--color-accent); animation: spin 1s linear infinite;" fill="none" viewBox="0 0 24 24">
        <circle style="opacity: 0.25;" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
        <path style="opacity: 0.75;" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <p style="margin-top: 16px; font-size: 18px; font-weight: 500; color: var(--color-text-primary);">
        Processing image {{ notesStore.currentImageIndex }} of {{ notesStore.images.length }}
      </p>
    </div>

    <!-- Main Content -->
    <div style="max-width: 900px; margin: 0 auto; padding: 48px 24px;">
    <!-- Header -->
    <div style="margin-bottom: 32px; text-align: center;">
      <h2 style="font-size: 28px; font-weight: 600; margin-bottom: 8px; color: var(--color-text-primary);">
        Upload Notes
      </h2>
      <p style="font-size: 16px; color: var(--color-text-muted);">
        Upload images of handwritten notes to convert to markdown
      </p>
    </div>

    <!-- Drop Zone (hidden when at max capacity) -->
    <div v-if="notesStore.canAddMore()" style="margin-bottom: 32px;">
      <DropZone @files-selected="handleFilesSelected" />
    </div>

    <!-- Max images reached message -->
    <div
      v-else
      style="margin-bottom: 32px; padding: 16px; border-radius: 8px; text-align: center; background-color: var(--color-surface); border: 1px solid var(--color-border);"
    >
      <p style="font-size: 14px; color: var(--color-text-muted);">
        Maximum of {{ notesStore.getMaxImages() }} images reached. Remove an image to add more.
      </p>
    </div>

    <!-- Image Previews -->
    <div v-if="notesStore.images.length > 0" style="margin-bottom: 32px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <p style="font-size: 14px; color: var(--color-text-muted); margin: 0;">
          {{ notesStore.images.length }}/{{ notesStore.getMaxImages() }} images
        </p>
        <button
          @click="notesStore.clearImages()"
          style="padding: 6px 12px; font-size: 13px; color: var(--color-text-muted); background: transparent; border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
          @mouseenter="$event.target.style.backgroundColor = 'var(--color-surface-hover)'"
          @mouseleave="$event.target.style.backgroundColor = 'transparent'"
        >
          Clear all
        </button>
      </div>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
        <ImagePreview
          v-for="image in notesStore.images"
          :key="image.id"
          :image="image"
          @remove="handleRemoveImage"
        />
      </div>
    </div>

    <!-- Options (checkboxes) -->
    <div style="display: flex; flex-wrap: wrap; gap: 24px; margin-bottom: 24px;">
      <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
        <input
          type="checkbox"
          v-model="notesStore.options.containsLatex"
          style="width: 18px; height: 18px; accent-color: #8b5cf6;"
        />
        <span style="font-size: 15px; color: var(--color-text-primary);">LaTeX equations</span>
      </label>

      <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
        <input
          type="checkbox"
          v-model="notesStore.options.containsDiagrams"
          style="width: 18px; height: 18px; accent-color: #8b5cf6;"
        />
        <span style="font-size: 15px; color: var(--color-text-primary);">Graphs & diagrams</span>
      </label>
    </div>

    <!-- Custom Instructions -->
    <div style="margin-bottom: 24px;">
      <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 12px;">
        <input
          type="checkbox"
          v-model="showCustomInstructions"
          style="width: 18px; height: 18px; accent-color: #8b5cf6;"
        />
        <span style="font-size: 15px; color: var(--color-text-primary);">Custom instructions</span>
      </label>
      <textarea
        v-show="showCustomInstructions"
        v-model="customInstructions"
        placeholder="e.g., Focus on mathematical equations, preserve table formatting, use bullet points for lists..."
        style="width: 100%; min-height: 80px; padding: 12px; font-size: 14px; font-family: inherit; line-height: 1.5; background-color: var(--color-surface); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 8px; resize: vertical; outline: none;"
      ></textarea>
    </div>

    <!-- Submit Button -->
    <div style="display: flex; justify-content: flex-end;">
      <button
        @click="handleSubmit"
        :disabled="notesStore.isProcessing"
        :style="{
          padding: '10px 24px',
          fontSize: '15px',
          fontWeight: '500',
          color: 'white',
          backgroundColor: 'var(--color-accent)',
          border: 'none',
          borderRadius: '24px',
          cursor: notesStore.isProcessing ? 'not-allowed' : 'pointer',
          opacity: notesStore.isProcessing ? '0.5' : '1'
        }"
        @mouseenter="!notesStore.isProcessing && ($event.target.style.backgroundColor = 'var(--color-accent-hover)')"
        @mouseleave="$event.target.style.backgroundColor = 'var(--color-accent)'"
      >
        Convert to Markdown
      </button>
    </div>

    <!-- No images message -->
    <div
      v-if="showNoImagesMessage"
      style="margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171;"
    >
      Please upload at least one image before processing.
    </div>

    <!-- Error Message -->
    <div
      v-if="notesStore.error"
      style="margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171;"
    >
      {{ notesStore.error }}
    </div>

    <!-- Dev Mode Test Button -->
    <div
      v-if="isDev"
      style="margin-top: 32px; padding-top: 24px; border-top: 1px dashed var(--color-border);"
    >
      <button
        @click="loadTestData"
        style="padding: 10px 20px; font-size: 14px; background-color: #f59e0b; color: white; border: none; border-radius: 6px; cursor: pointer;"
      >
        Load Test Data (Dev)
      </button>
    </div>
    </div>
  </div>
</template>

<style>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
