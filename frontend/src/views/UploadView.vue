<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotesStore } from '../stores/notes'
import { useConfigStore } from '../stores/config'
import { processSingleImage } from '../services/api'
import draggable from 'vuedraggable'
import DropZone from '../components/DropZone.vue'
import ImagePreview from '../components/ImagePreview.vue'

const router = useRouter()
const notesStore = useNotesStore()
const configStore = useConfigStore()
const showNoImagesMessage = ref(false)
const showCustomInstructions = ref(false)
const compareError = ref(null)
const isDev = import.meta.env.DEV

function handleCompareClick() {
  compareError.value = null
  const count = notesStore.images.length
  if (count === 0) {
    compareError.value = 'Upload an image first, then compare models.'
    return
  }
  if (count > 1) {
    compareError.value = 'Comparison only works on a single image. Remove the others or run them through the standard converter.'
    return
  }
  router.push('/compare')
}

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

  console.log('=== Starting OCR Processing (Parallel) ===')
  console.log(`Processing ${notesStore.images.length} image(s) in parallel`)
  console.log(`Options: LaTeX=${notesStore.options.containsLatex}, Diagrams=${notesStore.options.containsDiagrams}`)
  if (notesStore.customInstructions) {
    console.log(`Custom instructions: ${notesStore.customInstructions.substring(0, 100)}...`)
  }

  notesStore.setProcessing(true)
  notesStore.setError(null)

  const options = {
    ...notesStore.options,
    customInstructions: notesStore.customInstructions
  }

  try {
    // Launch all API calls in parallel
    const promises = notesStore.images.map((image, index) =>
      processSingleImage(image, options)
        .then(response => ({ status: 'fulfilled', value: response, image, index }))
        .catch(error => ({ status: 'rejected', reason: error, image, index }))
    )

    const results = await Promise.all(promises)

    const allResults = []
    const failures = []

    results.forEach((result) => {
      if (result.status === 'fulfilled' && result.value.success && result.value.results.length > 0) {
        allResults.push({
          ...result.value.results[0],
          preview: result.image.preview
        })
      } else {
        const filename = result.image.filename || `Image ${result.index + 1}`
        const errMsg = result.reason?.message || result.value?.error || 'Unknown error'
        failures.push({ filename, errMsg })
      }
    })

    console.log(`Processing complete. ${allResults.length} succeeded, ${failures.length} failed.`)
    if (failures.length > 0) {
      console.error('Failures:', failures)
    }

    if (failures.length > 0) {
      const grouped = new Map()
      for (const { filename, errMsg } of failures) {
        if (!grouped.has(errMsg)) grouped.set(errMsg, [])
        grouped.get(errMsg).push(filename)
      }
      const summary = [...grouped.entries()]
        .map(([msg, files]) => `${files.join(', ')}: ${msg}`)
        .join('\n')
      notesStore.setError(summary)
    }

    if (allResults.length === 0) {
      return
    }

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
        Processing {{ notesStore.images.length }} image{{ notesStore.images.length > 1 ? 's' : '' }}...
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
      <draggable
        :model-value="notesStore.images"
        @update:model-value="notesStore.setImages"
        item-key="id"
        handle=".drag-handle"
        :animation="200"
        ghost-class="drag-ghost"
        style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;"
      >
        <template #item="{ element }">
          <ImagePreview :image="element" @remove="handleRemoveImage" />
        </template>
      </draggable>
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
        v-model="notesStore.customInstructions"
        placeholder="e.g., Focus on mathematical equations, preserve table formatting, use bullet points for lists..."
        style="width: 100%; min-height: 80px; padding: 12px; font-size: 14px; font-family: inherit; line-height: 1.5; background-color: var(--color-surface); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 8px; resize: vertical; outline: none;"
      ></textarea>
    </div>

    <!-- Action Row: Compare (left) + Convert (right) -->
    <div style="display: flex; align-items: flex-start; gap: 16px;">
      <button
        @click="handleCompareClick"
        :disabled="!configStore.inferenceReady"
        :title="!configStore.inferenceReady ? 'Configure W&B credentials first' : 'Run all 3 models on a single image'"
        :style="{
          padding: '10px 24px',
          fontSize: '15px',
          fontWeight: '500',
          color: 'white',
          backgroundColor: 'var(--color-accent)',
          border: 'none',
          borderRadius: '24px',
          cursor: configStore.inferenceReady ? 'pointer' : 'not-allowed',
          opacity: configStore.inferenceReady ? '1' : '0.5'
        }"
        @mouseenter="configStore.inferenceReady && ($event.target.style.backgroundColor = 'var(--color-accent-hover)')"
        @mouseleave="$event.target.style.backgroundColor = 'var(--color-accent)'"
      >
        Compare models
      </button>

      <div style="margin-left: auto; display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
        <button
          @click="handleSubmit"
          :disabled="notesStore.isProcessing || !configStore.inferenceReady"
          :title="!configStore.inferenceReady ? 'Add your W&B credentials via the gear icon to enable conversion' : ''"
          :style="{
            padding: '10px 24px',
            fontSize: '15px',
            fontWeight: '500',
            color: 'white',
            backgroundColor: 'var(--color-accent)',
            border: 'none',
            borderRadius: '24px',
            cursor: (notesStore.isProcessing || !configStore.inferenceReady) ? 'not-allowed' : 'pointer',
            opacity: (notesStore.isProcessing || !configStore.inferenceReady) ? '0.5' : '1'
          }"
          @mouseenter="(!notesStore.isProcessing && configStore.inferenceReady) && ($event.target.style.backgroundColor = 'var(--color-accent-hover)')"
          @mouseleave="$event.target.style.backgroundColor = 'var(--color-accent)'"
        >
          Convert to Markdown
        </button>
        <p
          v-if="!configStore.inferenceReady"
          style="font-size: 13px; color: var(--color-text-muted); margin: 0;"
        >
          Add your W&amp;B API key, entity, and project via the
          <button
            type="button"
            @click="configStore.openModal('edit')"
            style="background: transparent; border: none; padding: 0; color: var(--color-accent); cursor: pointer; font-size: 13px; text-decoration: underline;"
          >gear icon</button>
          to enable conversion.
        </p>
      </div>
    </div>

    <!-- No images message -->
    <div
      v-if="showNoImagesMessage"
      style="margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171;"
    >
      Please upload at least one image before processing.
    </div>

    <!-- Compare validation message -->
    <div
      v-if="compareError"
      style="margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171;"
    >
      {{ compareError }}
    </div>

    <!-- Error Message -->
    <div
      v-if="notesStore.error"
      style="margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171; white-space: pre-wrap;"
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
.drag-ghost {
  opacity: 0.4;
}
.drag-handle:active {
  cursor: grabbing;
}
</style>
