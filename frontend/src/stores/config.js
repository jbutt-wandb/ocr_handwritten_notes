import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getConfigStatus, saveConfig as apiSaveConfig } from '../services/api'

export const useConfigStore = defineStore('config', () => {
  const status = ref(null)
  const isLoading = ref(false)
  const isModalOpen = ref(false)
  const modalMode = ref('firstRun')
  const skipped = ref(false)
  const lastError = ref(null)

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

  return {
    status,
    isLoading,
    isModalOpen,
    modalMode,
    skipped,
    lastError,
    openaiConfigured,
    fetchStatus,
    save,
    openModal,
    closeModal
  }
})
