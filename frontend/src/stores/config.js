import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { getConfigStatus, saveConfig as apiSaveConfig } from '../services/api'

export const SUPPORTED_PROVIDERS = ['openai', 'anthropic', 'gemini']

export const PROVIDER_LABELS = {
  openai: 'OpenAI',
  anthropic: 'Claude',
  gemini: 'Gemini'
}

const SELECTED_PROVIDER_STORAGE_KEY = 'likho.selectedProvider'

function loadSelectedProvider() {
  try {
    const stored = localStorage.getItem(SELECTED_PROVIDER_STORAGE_KEY)
    if (stored && SUPPORTED_PROVIDERS.includes(stored)) return stored
  } catch (_) {
    // localStorage may be unavailable (SSR, privacy mode); fall through to default
  }
  return 'openai'
}

export const useConfigStore = defineStore('config', () => {
  const status = ref(null)
  const isLoading = ref(false)
  const isModalOpen = ref(false)
  const modalMode = ref('firstRun')
  const skipped = ref(false)
  const lastError = ref(null)
  const selectedProvider = ref(loadSelectedProvider())

  watch(selectedProvider, (value) => {
    try {
      localStorage.setItem(SELECTED_PROVIDER_STORAGE_KEY, value)
    } catch (_) {
      // ignore
    }
  })

  const isSelectedProviderConfigured = computed(
    () => !!status.value?.[`${selectedProvider.value}_configured`]
  )

  const anyProviderConfigured = computed(() =>
    SUPPORTED_PROVIDERS.some((p) => !!status.value?.[`${p}_configured`])
  )

  // Backward-compat alias used in earlier UploadView code paths
  const openaiConfigured = computed(() => !!status.value?.openai_configured)

  async function fetchStatus() {
    isLoading.value = true
    lastError.value = null
    try {
      status.value = await getConfigStatus()
      return status.value
    } catch (err) {
      lastError.value = err.message || 'Could not load config status'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function save(payload) {
    isLoading.value = true
    lastError.value = null
    try {
      const result = await apiSaveConfig(payload)
      status.value = result
      return result
    } catch (err) {
      lastError.value = err.message || 'Save failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function openModal(mode = 'edit') {
    modalMode.value = mode
    isModalOpen.value = true
    lastError.value = null
  }

  function closeModal({ skip = false } = {}) {
    isModalOpen.value = false
    if (skip) {
      skipped.value = true
    }
  }

  function setSelectedProvider(name) {
    if (SUPPORTED_PROVIDERS.includes(name)) {
      selectedProvider.value = name
    }
  }

  return {
    status,
    isLoading,
    isModalOpen,
    modalMode,
    skipped,
    lastError,
    selectedProvider,
    isSelectedProviderConfigured,
    anyProviderConfigured,
    openaiConfigured,
    fetchStatus,
    save,
    openModal,
    closeModal,
    setSelectedProvider
  }
})
