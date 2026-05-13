<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import katex from 'katex'

import { useNotesStore } from '../stores/notes'
import { useConfigStore } from '../stores/config'
import { processCompare, saveConfig } from '../services/api'

const router = useRouter()
const notesStore = useNotesStore()
const configStore = useConfigStore()

const sourceImage = ref(null)            // { id, file, preview, filename } from notesStore
const showCostGate = ref(false)
const isRunning = ref(false)
const results = ref([])                  // [{ model_id, model_label, markdown, error }]
const activeIndex = ref(0)
const topLevelError = ref(null)
const viewMode = ref('preview')          // 'editor' | 'preview'

const hasResults = computed(() => results.value.length > 0)
const activeResult = computed(() => results.value[activeIndex.value] || null)

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

const renderedActive = computed(() => {
  const md = activeResult.value?.markdown
  if (!md) return ''
  return marked.parse(renderLatex(md))
})

async function runComparison() {
  showCostGate.value = false
  isRunning.value = true
  topLevelError.value = null
  results.value = []
  activeIndex.value = 0

  try {
    const data = await processCompare(
      { file: sourceImage.value.file },
      {
        containsLatex: notesStore.options.containsLatex,
        containsDiagrams: notesStore.options.containsDiagrams,
        customInstructions: notesStore.customInstructions
      }
    )
    results.value = data.results || []
    activeIndex.value = 0
  } catch (err) {
    topLevelError.value = err.message || 'Comparison failed'
  } finally {
    isRunning.value = false
  }
}

function navPrev() {
  if (results.value.length === 0) return
  activeIndex.value =
    (activeIndex.value - 1 + results.value.length) % results.value.length
}

function navNext() {
  if (results.value.length === 0) return
  activeIndex.value = (activeIndex.value + 1) % results.value.length
}

function handleKeydown(e) {
  if (!hasResults.value) return
  if (e.target?.tagName === 'TEXTAREA' || e.target?.tagName === 'INPUT') return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    navPrev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    navNext()
  }
}

onMounted(() => {
  const img = notesStore.images?.[0]
  if (!img) {
    router.replace('/')
    return
  }
  sourceImage.value = img
  showCostGate.value = true
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

function cancelCostGate() {
  showCostGate.value = false
  router.push('/')
}

async function useThisModel() {
  const result = activeResult.value
  if (!result || !result.markdown) return

  try {
    await saveConfig({ model: result.model_id })
    if (configStore.fetchStatus) {
      try { await configStore.fetchStatus() } catch (_) { /* ignore */ }
    }

    notesStore.setImages([sourceImage.value])
    notesStore.setResults([
      {
        filename: sourceImage.value.filename,
        markdown: result.markdown,
        preview: sourceImage.value.preview
      }
    ])

    router.push('/editor')
  } catch (err) {
    topLevelError.value = err.message || 'Could not switch to that model'
  }
}

function backToUpload() {
  router.push('/')
}
</script>

<template>
  <div>
    <!-- Loading overlay -->
    <div
      v-if="isRunning"
      style="position: fixed; inset: 0; background-color: rgba(0, 0, 0, 0.75); display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 9999;"
    >
      <svg style="width: 48px; height: 48px; color: var(--color-accent); animation: spin 1s linear infinite;" fill="none" viewBox="0 0 24 24">
        <circle style="opacity: 0.25;" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
        <path style="opacity: 0.75;" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <p style="margin-top: 16px; font-size: 18px; font-weight: 500; color: var(--color-text-primary);">
        Running 3 models on this image…
      </p>
      <p style="margin-top: 6px; font-size: 13px; color: var(--color-text-muted);">
        Kimi K2.5 · Gemma 4 31B · Qwen 3.5 35B
      </p>
    </div>

    <!-- Cost gate modal -->
    <div
      v-if="showCostGate"
      style="position: fixed; inset: 0; background-color: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; z-index: 10000; padding: 24px;"
      @click.self="cancelCostGate"
    >
      <div
        style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; max-width: 480px; width: 100%; padding: 28px;"
      >
        <h2 style="font-size: 20px; font-weight: 700; color: var(--color-text-primary); margin: 0 0 12px 0;">
          Run all 3 vision models on this image?
        </h2>
        <p style="font-size: 14px; color: var(--color-text-muted); line-height: 1.55; margin: 0 0 20px 0;">
          We'll call <strong style="color: var(--color-text-primary);">Kimi K2.5</strong>,
          <strong style="color: var(--color-text-primary);">Gemma 4 31B</strong>, and
          <strong style="color: var(--color-text-primary);">Qwen 3.5 35B</strong> in parallel.
          That's 3× the W&amp;B Inference cost and roughly 3× the wall-clock latency
          of a normal OCR run.
        </p>
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button
            @click="cancelCostGate"
            style="padding: 10px 16px; font-size: 14px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
          >
            Cancel
          </button>
          <button
            @click="runComparison"
            style="padding: 10px 20px; font-size: 14px; font-weight: 500; color: white; background-color: var(--color-accent); border: none; border-radius: 6px; cursor: pointer;"
          >
            Run all 3
          </button>
        </div>
      </div>
    </div>

    <!-- Result view -->
    <div v-if="hasResults" style="max-width: 1280px; margin: 0 auto; padding: 32px 24px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
        <button
          @click="backToUpload"
          style="padding: 8px 14px; font-size: 13px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
        >
          ← Back to upload
        </button>
        <div style="font-size: 13px; color: var(--color-text-muted);">
          Use ← / → to switch models
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1.4fr; gap: 24px; align-items: start;">
        <!-- Image (sticky) -->
        <div style="position: sticky; top: 24px;">
          <div style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 16px;">
            <p style="font-size: 13px; color: var(--color-text-muted); margin: 0 0 10px 0;">
              {{ sourceImage?.filename }}
            </p>
            <img
              :src="sourceImage?.preview"
              :alt="sourceImage?.filename"
              style="width: 100%; max-height: 75vh; object-fit: contain; border-radius: 8px;"
            />
          </div>
        </div>

        <!-- Active result -->
        <div style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; display: flex; flex-direction: column; min-height: 60vh;">
          <!-- Header: prev / position+label / next -->
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--color-border);">
            <button
              @click="navPrev"
              :disabled="results.length < 2"
              :style="{
                padding: '6px 12px',
                fontSize: '16px',
                background: 'transparent',
                color: 'var(--color-text-muted)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                cursor: results.length < 2 ? 'not-allowed' : 'pointer',
                opacity: results.length < 2 ? '0.4' : '1'
              }"
              aria-label="Previous model"
            >◀</button>

            <div style="text-align: center;">
              <div style="font-size: 12px; color: var(--color-text-muted); letter-spacing: 0.05em; text-transform: uppercase;">
                {{ activeIndex + 1 }} / {{ results.length }}
              </div>
              <div style="font-size: 18px; font-weight: 600; color: var(--color-text-primary); margin-top: 2px;">
                {{ activeResult?.model_label }}
              </div>
            </div>

            <button
              @click="navNext"
              :disabled="results.length < 2"
              :style="{
                padding: '6px 12px',
                fontSize: '16px',
                background: 'transparent',
                color: 'var(--color-text-muted)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                cursor: results.length < 2 ? 'not-allowed' : 'pointer',
                opacity: results.length < 2 ? '0.4' : '1'
              }"
              aria-label="Next model"
            >▶</button>
          </div>

          <!-- View mode toggle -->
          <div style="display: flex; justify-content: center; padding: 10px 18px; border-bottom: 1px solid var(--color-border);">
            <div style="display: inline-flex; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 8px; padding: 2px;">
              <button
                @click="viewMode = 'editor'"
                :style="{
                  padding: '6px 16px',
                  fontSize: '13px',
                  fontWeight: '500',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  backgroundColor: viewMode === 'editor' ? 'var(--color-accent)' : 'transparent',
                  color: viewMode === 'editor' ? 'white' : 'var(--color-text-muted)'
                }"
              >Editor</button>
              <button
                @click="viewMode = 'preview'"
                :style="{
                  padding: '6px 16px',
                  fontSize: '13px',
                  fontWeight: '500',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  backgroundColor: viewMode === 'preview' ? 'var(--color-accent)' : 'transparent',
                  color: viewMode === 'preview' ? 'white' : 'var(--color-text-muted)'
                }"
              >Preview</button>
            </div>
          </div>

          <!-- Body -->
          <div style="padding: 20px; flex: 1; overflow-y: auto; max-height: 70vh;">
            <div
              v-if="activeResult?.error"
              style="padding: 14px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171; white-space: pre-wrap;"
            >
              <strong>{{ activeResult.model_label }} failed:</strong>
              <br />
              {{ activeResult.error }}
            </div>
            <textarea
              v-else-if="viewMode === 'editor'"
              v-model="results[activeIndex].markdown"
              spellcheck="false"
              style="width: 100%; min-height: 60vh; padding: 12px; font-size: 14px; font-family: ui-monospace, monospace; line-height: 1.55; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 8px; resize: vertical; outline: none; box-sizing: border-box;"
            ></textarea>
            <div
              v-else
              class="markdown-preview"
              style="font-size: 15px; line-height: 1.65; color: var(--color-text-primary);"
              v-html="renderedActive"
            ></div>
          </div>

          <!-- Footer action -->
          <div style="padding: 14px 18px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end;">
            <button
              @click="useThisModel"
              :disabled="!activeResult?.markdown"
              :style="{
                padding: '10px 20px',
                fontSize: '14px',
                fontWeight: '500',
                color: 'white',
                backgroundColor: 'var(--color-accent)',
                border: 'none',
                borderRadius: '8px',
                cursor: activeResult?.markdown ? 'pointer' : 'not-allowed',
                opacity: activeResult?.markdown ? '1' : '0.5'
              }"
            >
              Use {{ activeResult?.model_label }} for OCR →
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="topLevelError"
        style="margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171; white-space: pre-wrap;"
      >
        {{ topLevelError }}
      </div>
    </div>

    <!-- Pre-results error fallback (e.g. comparison API failed) -->
    <div
      v-else-if="!showCostGate && !isRunning && topLevelError"
      style="max-width: 600px; margin: 80px auto; padding: 24px; text-align: center;"
    >
      <p style="padding: 12px; border-radius: 8px; font-size: 14px; background-color: rgba(239, 68, 68, 0.1); color: #f87171; white-space: pre-wrap; margin-bottom: 16px;">
        {{ topLevelError }}
      </p>
      <button
        @click="backToUpload"
        style="padding: 10px 16px; font-size: 14px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
      >
        ← Back to upload
      </button>
    </div>
  </div>
</template>

<style>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.markdown-preview h1 { font-size: 22px; font-weight: 700; margin: 18px 0 10px; }
.markdown-preview h2 { font-size: 19px; font-weight: 700; margin: 16px 0 8px; }
.markdown-preview h3 { font-size: 17px; font-weight: 600; margin: 14px 0 8px; }
.markdown-preview p { margin: 8px 0; }
.markdown-preview ul, .markdown-preview ol { margin: 8px 0; padding-left: 22px; }
.markdown-preview li { margin: 4px 0; }
.markdown-preview code { background: var(--color-bg); padding: 2px 5px; border-radius: 4px; font-family: ui-monospace, monospace; font-size: 13px; }
.markdown-preview pre { background: var(--color-bg); padding: 12px; border-radius: 8px; overflow-x: auto; }
.markdown-preview blockquote { border-left: 3px solid var(--color-accent); padding-left: 12px; color: var(--color-text-muted); margin: 12px 0; }
</style>
