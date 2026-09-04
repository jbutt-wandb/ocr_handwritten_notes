<script setup>
import { ref, computed, watch } from 'vue'
import { useConfigStore, SUPPORTED_PROVIDERS, PROVIDER_LABELS } from '../stores/config'
import { fetchLocalModels } from '../services/api'

const DEFAULT_LOCAL_BASE_URL = 'http://localhost:11434/v1'

const configStore = useConfigStore()

const keyInput = ref('')
const showKey = ref(false)
const localError = ref(null)
const modalProvider = ref(configStore.selectedProvider)

const baseUrlInput = ref(DEFAULT_LOCAL_BASE_URL)
const modelInput = ref('')
const localModels = ref([])
const modelsState = ref('idle') // 'idle' | 'loading' | 'loaded' | 'error'
const modelsError = ref(null)
const useManualModel = ref(false)

const isFirstRun = computed(() => configStore.modalMode === 'firstRun')
const status = computed(() => configStore.status)
const activeLabel = computed(() => PROVIDER_LABELS[modalProvider.value])
const activeFieldName = computed(() => `${modalProvider.value}_api_key`)
const isLocal = computed(() => modalProvider.value === 'local')

const activeConfigured = computed(
  () => !!status.value?.[`${modalProvider.value}_configured`]
)
const activePreview = computed(() => status.value?.[`${modalProvider.value}_preview`] || '')
const activeSource = computed(() => status.value?.[`${modalProvider.value}_source`] || 'none')

const placeholderForProvider = {
  openai: 'sk-...',
  anthropic: 'sk-ant-...',
  gemini: 'AIza...',
  mistral: 'mistral key…',
  local: 'usually not needed'
}

const placeholder = computed(() => {
  if (isLocal.value) return placeholderForProvider.local
  return activePreview.value
    ? `current: ${activePreview.value}`
    : placeholderForProvider[modalProvider.value] || 'API key'
})

function resetLocalFields() {
  baseUrlInput.value = status.value?.local_base_url || DEFAULT_LOCAL_BASE_URL
  modelInput.value = status.value?.local_model || ''
  localModels.value = []
  modelsState.value = 'idle'
  modelsError.value = null
  useManualModel.value = false
}

async function refreshModels() {
  modelsState.value = 'loading'
  modelsError.value = null
  try {
    const models = await fetchLocalModels({
      baseUrl: baseUrlInput.value.trim(),
      apiKey: keyInput.value.trim()
    })
    localModels.value = models
    modelsState.value = 'loaded'
    // Keep the saved model selected if the server still serves it.
    if (!models.includes(modelInput.value)) {
      modelInput.value = models[0] || ''
    }
  } catch (err) {
    localModels.value = []
    modelsState.value = 'error'
    modelsError.value = err.message
  }
}

watch(
  () => configStore.isModalOpen,
  (open) => {
    if (open) {
      modalProvider.value = configStore.selectedProvider
      keyInput.value = ''
      showKey.value = false
      localError.value = null
      if (isLocal.value) {
        resetLocalFields()
        refreshModels()
      }
    }
  }
)

watch(modalProvider, () => {
  keyInput.value = ''
  showKey.value = false
  localError.value = null
  if (isLocal.value) {
    resetLocalFields()
    refreshModels()
  }
})

async function handleSave() {
  localError.value = null

  const payload = {}
  if (isLocal.value) {
    const baseUrl = baseUrlInput.value.trim()
    const model = modelInput.value.trim()
    if (!baseUrl || !model) {
      localError.value = 'Server URL and model are required'
      return
    }
    payload.local_base_url = baseUrl
    payload.local_model = model
    if (keyInput.value.trim()) {
      payload.local_api_key = keyInput.value.trim()
    }
  } else {
    const willBeConfigured = activeConfigured.value || !!keyInput.value.trim()
    if (!willBeConfigured) {
      localError.value = `${activeLabel.value} API key is required`
      return
    }
    if (keyInput.value.trim()) {
      payload[activeFieldName.value] = keyInput.value.trim()
    }
  }

  try {
    if (Object.keys(payload).length > 0) {
      await configStore.save(payload)
    }
    configStore.setSelectedProvider(modalProvider.value)
    configStore.closeModal()
  } catch (err) {
    localError.value = configStore.lastError || err.message
  }
}

function handleSkip() {
  configStore.closeModal({ skip: true })
}

function handleCancel() {
  configStore.closeModal()
}

function isProviderConfigured(name) {
  return !!status.value?.[`${name}_configured`]
}
</script>

<template>
  <div
    v-if="configStore.isModalOpen"
    style="position: fixed; inset: 0; background-color: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; z-index: 10000; padding: 24px;"
    @click.self="!isFirstRun && handleCancel()"
  >
    <div
      style="background-color: var(--color-surface); border: 1px solid var(--color-border); max-width: 520px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 28px;"
    >
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <h2 style="font-family: 'EB Garamond', Georgia, serif; font-size: 26px; font-weight: 400; letter-spacing: 0.5px; color: var(--color-text-primary); margin: 0;">
          {{ isFirstRun ? 'Welcome to Likho' : 'Credentials' }}
        </h2>
        <button
          v-if="!isFirstRun"
          @click="handleCancel"
          aria-label="Close"
          style="background: transparent; border: none; color: var(--color-text-muted); font-size: 22px; cursor: pointer; line-height: 1;"
        >
          ×
        </button>
      </div>
      <p style="font-size: 14px; color: var(--color-text-muted); margin: 0 0 20px 0; line-height: 1.5;">
        {{ isFirstRun
          ? 'Pick a provider and add its API key to enable OCR. Stored locally in .likho_config.json.'
          : 'Update API keys for any provider. The existing value stays unless you enter a new one.' }}
      </p>

      <!-- Provider dropdown -->
      <div style="margin-bottom: 18px;">
        <label style="display: block; font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 8px;">
          Provider
        </label>
        <select
          v-model="modalProvider"
          style="width: 100%; padding: 10px 12px; font-size: 14px; font-family: 'Crimson Pro', Georgia, serif; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none; cursor: pointer;"
        >
          <option v-for="name in SUPPORTED_PROVIDERS" :key="name" :value="name">
            {{ PROVIDER_LABELS[name] }}{{ isProviderConfigured(name) ? ' ✓' : '' }}
          </option>
        </select>
      </div>

      <!-- Local server settings -->
      <template v-if="isLocal">
        <div style="margin-bottom: 18px;">
          <label style="display: block; font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 6px;">
            Server URL <span style="color: #f87171;">*</span>
            <span v-if="activeConfigured" style="font-weight: 400; color: var(--color-text-muted); margin-left: 6px;">
              ({{ activePreview }} from {{ activeSource }})
            </span>
          </label>
          <div style="display: flex; gap: 8px;">
            <input
              type="text"
              v-model="baseUrlInput"
              placeholder="http://localhost:11434/v1"
              autocomplete="off"
              spellcheck="false"
              @change="refreshModels"
              style="flex: 1; padding: 10px 12px; font-size: 14px; font-family: ui-monospace, monospace; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none;"
            />
            <button
              type="button"
              @click="refreshModels"
              :disabled="modelsState === 'loading'"
              style="padding: 0 12px; font-size: 12px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer; white-space: nowrap;"
            >
              {{ modelsState === 'loading' ? 'Checking…' : 'Refresh models' }}
            </button>
          </div>
          <p style="font-size: 12px; color: var(--color-text-muted); margin: 6px 0 0 0; line-height: 1.4;">
            Ollama default shown; also works with LM Studio, vLLM, or any OpenAI-compatible server.
            Running the backend in Docker? Use http://host.docker.internal:11434/v1
          </p>
        </div>

        <div style="margin-bottom: 18px;">
          <label style="display: block; font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 6px;">
            Model <span style="color: #f87171;">*</span>
          </label>
          <select
            v-if="modelsState === 'loaded' && !useManualModel"
            v-model="modelInput"
            style="width: 100%; padding: 10px 12px; font-size: 14px; font-family: ui-monospace, monospace; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none; cursor: pointer;"
          >
            <option v-for="model in localModels" :key="model" :value="model">{{ model }}</option>
          </select>
          <input
            v-else
            type="text"
            v-model="modelInput"
            placeholder="e.g. llama3.2-vision"
            autocomplete="off"
            spellcheck="false"
            style="width: 100%; padding: 10px 12px; font-size: 14px; font-family: ui-monospace, monospace; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none;"
          />
          <p v-if="modelsState === 'loaded'" style="font-size: 12px; color: var(--color-text-muted); margin: 6px 0 0 0;">
            Connected — {{ localModels.length }} model{{ localModels.length === 1 ? '' : 's' }} found.
            Pick a vision-capable one.
            <button
              type="button"
              @click="useManualModel = !useManualModel"
              style="background: transparent; border: none; color: var(--color-text-muted); font-size: 12px; text-decoration: underline; cursor: pointer; padding: 0;"
            >
              {{ useManualModel ? 'Choose from list' : 'Enter manually' }}
            </button>
          </p>
          <p v-else-if="modelsState === 'error'" style="font-size: 12px; color: #f87171; margin: 6px 0 0 0; line-height: 1.4;">
            {{ modelsError }} You can still type a model name manually.
          </p>
        </div>
      </template>

      <!-- Conditional key input -->
      <div style="margin-bottom: 18px;">
        <label style="display: block; font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 6px;">
          <template v-if="isLocal">API Key <span style="font-weight: 400; color: var(--color-text-muted);">(optional)</span></template>
          <template v-else>{{ activeLabel }} API Key <span style="color: #f87171;">*</span></template>
          <span v-if="activeConfigured && !isLocal" style="font-weight: 400; color: var(--color-text-muted); margin-left: 6px;">
            ({{ activePreview }} from {{ activeSource }})
          </span>
        </label>
        <div style="display: flex; gap: 8px;">
          <input
            :type="showKey ? 'text' : 'password'"
            v-model="keyInput"
            :placeholder="placeholder"
            autocomplete="off"
            spellcheck="false"
            style="flex: 1; padding: 10px 12px; font-size: 14px; font-family: ui-monospace, monospace; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none;"
          />
          <button
            type="button"
            @click="showKey = !showKey"
            style="padding: 0 12px; font-size: 12px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
          >
            {{ showKey ? 'Hide' : 'Show' }}
          </button>
        </div>
      </div>

      <!-- Errors -->
      <div v-if="localError" style="margin-top: 16px; padding: 10px 12px; border-radius: 6px; font-size: 13px; background-color: rgba(239, 68, 68, 0.1); color: #f87171;">
        {{ localError }}
      </div>

      <!-- Footer buttons -->
      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px;">
        <button
          v-if="isFirstRun"
          @click="handleSkip"
          :disabled="configStore.isLoading"
          class="btn-likho-ghost"
        >
          Skip for now
        </button>
        <button
          v-else
          @click="handleCancel"
          :disabled="configStore.isLoading"
          class="btn-likho-ghost"
        >
          Cancel
        </button>
        <button
          @click="handleSave"
          :disabled="configStore.isLoading"
          class="btn-likho-primary"
        >
          {{ configStore.isLoading ? 'Saving…' : 'Save' }}
        </button>
      </div>
    </div>
  </div>
</template>
