<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useNotesStore } from '../stores/notes'
import { useConfigStore } from '../stores/config'
import { marked } from 'marked'
import katex from 'katex'
import DropZone from '../components/DropZone.vue'
import { processSingleImage } from '../services/api'

const router = useRouter()
const notesStore = useNotesStore()
const configStore = useConfigStore()
const viewMode = ref('editor')
const editorContent = ref('')
const documentTitle = ref('Untitled Document')

// Add Image Modal state
const showAddModal = ref(false)
const addImages = ref([])
const addOptions = ref({
  containsLatex: false,
  containsDiagrams: false,
  customInstructions: ''
})
const isAddProcessing = ref(false)
const addError = ref(null)

onMounted(() => {
  if (notesStore.results.length === 0) {
    router.push('/')
  } else {
    // Combine all markdown into single editor (no dividers)
    editorContent.value = notesStore.results
      .map(r => r.markdown)
      .join('\n\n')
  }
})

function renderLatex(text) {
  if (!text) return ''

  let result = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, latex) => {
    try {
      return katex.renderToString(latex.trim(), { displayMode: true, throwOnError: false })
    } catch {
      return `<span style="color: #f87171;">${match}</span>`
    }
  })

  result = result.replace(/(?<!\$)\$(?!\$)([^\$\n]+?)\$(?!\$)/g, (match, latex) => {
    try {
      return katex.renderToString(latex.trim(), { displayMode: false, throwOnError: false })
    } catch {
      return `<span style="color: #f87171;">${match}</span>`
    }
  })

  return result
}

const renderedPreview = computed(() => {
  if (!editorContent.value) return ''
  const withLatex = renderLatex(editorContent.value)
  return marked.parse(withLatex)
})

function downloadMarkdown() {
  const blob = new Blob([editorContent.value], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)

  // Use document title as filename, sanitize it
  const filename = documentTitle.value.trim().replace(/[^a-zA-Z0-9-_ ]/g, '').replace(/\s+/g, '_') || 'notes'

  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}.md`
  link.click()

  URL.revokeObjectURL(url)
}

function goBack() {
  router.push('/')
}

function handleTab(event) {
  if (event.key === 'Tab') {
    event.preventDefault()
    const textarea = event.target
    const start = textarea.selectionStart
    const end = textarea.selectionEnd

    const spaces = '  '
    editorContent.value =
      editorContent.value.substring(0, start) +
      spaces +
      editorContent.value.substring(end)

    nextTick(() => {
      textarea.selectionStart = textarea.selectionEnd = start + spaces.length
    })
  }
}

// Add Image Modal functions
function handleAddFiles(files) {
  files.forEach(file => {
    const reader = new FileReader()
    reader.onload = (e) => {
      addImages.value.push({
        id: crypto.randomUUID(),
        file: file,
        preview: e.target.result,
        filename: file.name
      })
    }
    reader.readAsDataURL(file)
  })
}

function removeAddImage(id) {
  addImages.value = addImages.value.filter(img => img.id !== id)
}

async function processAddImages() {
  if (addImages.value.length === 0) return

  isAddProcessing.value = true
  addError.value = null

  try {
    for (const image of addImages.value) {
      const response = await processSingleImage(image, {
        containsLatex: addOptions.value.containsLatex,
        containsDiagrams: addOptions.value.containsDiagrams,
        customInstructions: addOptions.value.customInstructions,
        provider: configStore.selectedProvider
      })

      if (response.success && response.results.length > 0) {
        // Append markdown to editor
        editorContent.value += '\n\n' + response.results[0].markdown

        // Add to results for left panel display
        notesStore.results.push({
          ...response.results[0],
          preview: image.preview
        })
      } else {
        throw new Error(response.error || 'Failed to process image')
      }
    }

    // Success - close modal and reset
    showAddModal.value = false
    addImages.value = []
    addOptions.value = { containsLatex: false, containsDiagrams: false, customInstructions: '' }
  } catch (err) {
    addError.value = err.message
  } finally {
    isAddProcessing.value = false
  }
}

function closeAddModal() {
  showAddModal.value = false
  addImages.value = []
  addError.value = null
}
</script>

<template>
  <div style="height: calc(100vh - 61px); display: flex; flex-direction: column;">
    <!-- Toolbar -->
    <div style="padding: 12px 24px; background-color: var(--color-surface); border-bottom: 1px solid var(--color-border); display: flex; align-items: center; justify-content: space-between;">
      <div style="display: flex; gap: 8px;">
        <button
          @click="goBack"
          style="padding: 8px 16px; font-size: 14px; border-radius: 6px; background: transparent; border: 1px solid var(--color-border); cursor: pointer; color: var(--color-text-primary);"
          @mouseenter="$event.target.style.backgroundColor = 'var(--color-surface-hover)'"
          @mouseleave="$event.target.style.backgroundColor = 'transparent'"
        >
          Back
        </button>
        <button
          @click="showAddModal = true"
          style="padding: 8px 16px; font-size: 14px; border-radius: 6px; background: transparent; border: 1px solid var(--color-border); cursor: pointer; color: var(--color-text-primary);"
          @mouseenter="$event.target.style.backgroundColor = 'var(--color-surface-hover)'"
          @mouseleave="$event.target.style.backgroundColor = 'transparent'"
        >
          Add Image
        </button>
      </div>

      <div style="display: flex; align-items: center; gap: 4px; background-color: var(--color-bg); border-radius: 8px; padding: 4px;">
        <button
          @click="viewMode = 'editor'"
          :style="{
            padding: '8px 16px',
            fontSize: '14px',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: viewMode === 'editor' ? 'var(--color-accent)' : 'transparent',
            color: viewMode === 'editor' ? 'white' : 'var(--color-text-muted)'
          }"
        >
          Editor
        </button>
        <button
          @click="viewMode = 'preview'"
          :style="{
            padding: '8px 16px',
            fontSize: '14px',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: viewMode === 'preview' ? 'var(--color-accent)' : 'transparent',
            color: viewMode === 'preview' ? 'white' : 'var(--color-text-muted)'
          }"
        >
          Preview
        </button>
      </div>
    </div>

    <!-- Main content -->
    <div style="flex: 1; display: flex; overflow: hidden;">
      <!-- Left: Images -->
      <div style="width: 35%; border-right: 1px solid var(--color-border); overflow-y: auto; padding: 16px;">
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div
            v-for="(result, index) in notesStore.results"
            :key="index"
            style="border-radius: 8px; overflow: hidden; border: 1px solid var(--color-border);"
          >
            <img
              :src="result.preview"
              :alt="result.filename"
              style="width: 100%; display: block;"
            />
            <div style="padding: 8px 12px; background-color: var(--color-surface); border-top: 1px solid var(--color-border);">
              <span style="font-size: 12px; color: var(--color-text-muted);">{{ result.filename }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Editor or Preview -->
      <div style="flex: 1; display: flex; flex-direction: column; padding: 16px; gap: 12px; overflow: hidden;">
        <!-- Document Title Input (always visible) -->
        <div>
          <label style="display: block; font-size: 12px; font-weight: 500; color: var(--color-text-muted); margin-bottom: 6px;">
            Document Title
          </label>
          <input
            v-model="documentTitle"
            type="text"
            placeholder="Enter document title..."
            style="width: 100%; padding: 10px 14px; font-size: 16px; font-weight: 500; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 8px; outline: none;"
          />
        </div>

        <!-- Editor Mode -->
        <textarea
          v-if="viewMode === 'editor'"
          v-model="editorContent"
          @keydown="handleTab"
          style="flex: 1; width: 100%; padding: 16px; font-family: ui-monospace, monospace; font-size: 14px; line-height: 1.6; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 8px; resize: none; outline: none;"
          placeholder="Markdown content..."
        ></textarea>

        <!-- Preview Mode -->
        <div
          v-else
          style="flex: 1; overflow-y: auto; padding: 16px; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 8px;"
          class="prose prose-invert"
          v-html="renderedPreview"
        ></div>
      </div>
    </div>

    <!-- Download button (bottom right) -->
    <button
      @click="downloadMarkdown"
      style="position: fixed; bottom: 24px; right: 24px; padding: 12px 24px; font-size: 15px; font-weight: 500; color: white; background-color: var(--color-accent); border: none; border-radius: 24px; cursor: pointer; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);"
      @mouseenter="$event.target.style.backgroundColor = 'var(--color-accent-hover)'"
      @mouseleave="$event.target.style.backgroundColor = 'var(--color-accent)'"
    >
      <svg style="width: 18px; height: 18px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      Download
    </button>

    <!-- Add Image Modal -->
    <div
      v-if="showAddModal"
      style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 9999;"
    >
      <div style="background: var(--color-surface); border-radius: 12px; padding: 24px; width: 500px; max-height: 80vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; font-size: 18px; font-weight: 600; color: var(--color-text-primary);">Add More Images</h3>
          <button
            @click="closeAddModal"
            style="background: none; border: none; cursor: pointer; color: var(--color-text-muted); font-size: 20px;"
          >&times;</button>
        </div>

        <!-- Drop Zone -->
        <div style="margin-bottom: 16px;">
          <DropZone @files-selected="handleAddFiles" />
        </div>

        <!-- Preview added images -->
        <div v-if="addImages.length > 0" style="margin-bottom: 16px;">
          <p style="font-size: 14px; color: var(--color-text-muted); margin-bottom: 8px;">
            {{ addImages.length }} image(s) selected
          </p>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <div
              v-for="img in addImages"
              :key="img.id"
              style="position: relative; width: 80px; height: 80px; border-radius: 6px; overflow: hidden; border: 1px solid var(--color-border);"
            >
              <img :src="img.preview" style="width: 100%; height: 100%; object-fit: cover;" />
              <button
                @click="removeAddImage(img.id)"
                style="position: absolute; top: 2px; right: 2px; width: 20px; height: 20px; border-radius: 50%; background: rgba(0,0,0,0.6); border: none; color: white; cursor: pointer; font-size: 12px;"
              >&times;</button>
            </div>
          </div>
        </div>

        <!-- Options -->
        <div style="margin-bottom: 16px;">
          <div style="display: flex; gap: 16px; margin-bottom: 12px;">
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
              <input type="checkbox" v-model="addOptions.containsLatex" style="width: 16px; height: 16px; accent-color: #8b5cf6;" />
              <span style="font-size: 14px; color: var(--color-text-primary);">LaTeX equations</span>
            </label>
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
              <input type="checkbox" v-model="addOptions.containsDiagrams" style="width: 16px; height: 16px; accent-color: #8b5cf6;" />
              <span style="font-size: 14px; color: var(--color-text-primary);">Diagrams</span>
            </label>
          </div>
          <textarea
            v-model="addOptions.customInstructions"
            placeholder="Custom instructions (optional)..."
            style="width: 100%; min-height: 60px; padding: 10px; font-size: 14px; font-family: inherit; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; resize: vertical; outline: none;"
          ></textarea>
        </div>

        <!-- Error -->
        <div
          v-if="addError"
          style="margin-bottom: 16px; padding: 10px; border-radius: 6px; background-color: rgba(239, 68, 68, 0.1); color: #f87171; font-size: 14px;"
        >
          {{ addError }}
        </div>

        <!-- Buttons -->
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <button
            @click="closeAddModal"
            style="padding: 8px 16px; font-size: 14px; border-radius: 6px; background: transparent; border: 1px solid var(--color-border); cursor: pointer; color: var(--color-text-primary);"
          >
            Cancel
          </button>
          <button
            @click="processAddImages"
            :disabled="isAddProcessing || addImages.length === 0"
            :style="{
              padding: '8px 16px',
              fontSize: '14px',
              borderRadius: '6px',
              border: 'none',
              cursor: isAddProcessing || addImages.length === 0 ? 'not-allowed' : 'pointer',
              backgroundColor: 'var(--color-accent)',
              color: 'white',
              opacity: isAddProcessing || addImages.length === 0 ? '0.5' : '1'
            }"
          >
            {{ isAddProcessing ? 'Processing...' : 'Process' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
.prose {
  color: var(--color-text-primary);
  line-height: 1.7;
}
.prose h1, .prose h2, .prose h3, .prose h4 {
  color: var(--color-text-primary);
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}
.prose h1 { font-size: 2em; font-weight: 700; }
.prose h2 { font-size: 1.5em; font-weight: 600; }
.prose h3 { font-size: 1.25em; font-weight: 600; }
.prose p { margin: 1em 0; }
.prose ul, .prose ol { margin: 1em 0; padding-left: 1.5em; }
.prose li { margin: 0.25em 0; }
.prose code {
  background-color: var(--color-bg);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
}
.prose pre {
  background-color: var(--color-bg);
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
}
.prose hr {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 2em 0;
}
</style>
