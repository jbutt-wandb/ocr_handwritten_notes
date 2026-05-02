<script setup>
import { ref, computed, watch } from 'vue'
import { useConfigStore, SUPPORTED_PROVIDERS, PROVIDER_LABELS } from '../stores/config'

const configStore = useConfigStore()

const keyInput = ref('')
const showKey = ref(false)
const localError = ref(null)

const isFirstRun = computed(() => configStore.modalMode === 'firstRun')
const status = computed(() => configStore.status)
const activeProvider = computed(() => configStore.selectedProvider)
const activeLabel = computed(() => PROVIDER_LABELS[activeProvider.value])
const activeFieldName = computed(() => `${activeProvider.value}_api_key`)

const activeConfigured = computed(
  () => !!status.value?.[`${activeProvider.value}_configured`]
)
const activePreview = computed(() => status.value?.[`${activeProvider.value}_preview`] || '')
const activeSource = computed(() => status.value?.[`${activeProvider.value}_source`] || 'none')

const placeholderForProvider = {
  openai: 'sk-...',
  anthropic: 'sk-ant-...',
  gemini: 'AIza...'
}

const placeholder = computed(() =>
  activePreview.value
    ? `current: ${activePreview.value}`
    : placeholderForProvider[activeProvider.value] || 'API key'
)

watch(
  () => configStore.isModalOpen,
  (open) => {
    if (open) {
      keyInput.value = ''
      showKey.value = false
      localError.value = null
    }
  }
)

watch(activeProvider, () => {
  keyInput.value = ''
  showKey.value = false
  localError.value = null
})

function selectProvider(name) {
  configStore.setSelectedProvider(name)
}

async function handleSave() {
  localError.value = null

  if (!activeConfigured.value && !keyInput.value.trim()) {
    localError.value = `${activeLabel.value} API key is required`
    return
  }

  const payload = {}
  if (keyInput.value.trim()) {
    payload[activeFieldName.value] = keyInput.value.trim()
  }

  if (Object.keys(payload).length === 0) {
    configStore.closeModal()
    return
  }

  try {
    await configStore.save(payload)
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
      style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; max-width: 520px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 28px;"
    >
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <h2 style="font-size: 22px; font-weight: 700; color: var(--color-text-primary); margin: 0;">
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

      <!-- Provider radio -->
      <div style="margin-bottom: 18px;">
        <div style="font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 8px;">
          Provider
        </div>
        <div style="display: flex; gap: 8px;">
          <label
            v-for="name in SUPPORTED_PROVIDERS"
            :key="name"
            :style="{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '10px 12px',
              fontSize: '13px',
              fontWeight: '500',
              color: activeProvider === name ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
              backgroundColor: activeProvider === name ? 'var(--color-bg)' : 'transparent',
              border: `1px solid ${activeProvider === name ? 'var(--color-accent)' : 'var(--color-border)'}`,
              borderRadius: '6px',
              cursor: 'pointer',
              userSelect: 'none'
            }"
          >
            <input
              type="radio"
              name="provider"
              :value="name"
              :checked="activeProvider === name"
              @change="selectProvider(name)"
              style="display: none;"
            />
            <span>{{ PROVIDER_LABELS[name] }}</span>
            <span
              v-if="isProviderConfigured(name)"
              :style="{ color: '#22c55e', fontSize: '13px', fontWeight: '700' }"
              aria-label="Configured"
            >✓</span>
          </label>
        </div>
      </div>

      <!-- Conditional key input -->
      <div style="margin-bottom: 18px;">
        <label style="display: block; font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 6px;">
          {{ activeLabel }} API Key <span style="color: #f87171;">*</span>
          <span v-if="activeConfigured" style="font-weight: 400; color: var(--color-text-muted); margin-left: 6px;">
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
          style="padding: 10px 16px; font-size: 14px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
        >
          Skip for now
        </button>
        <button
          v-else
          @click="handleCancel"
          :disabled="configStore.isLoading"
          style="padding: 10px 16px; font-size: 14px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
        >
          Cancel
        </button>
        <button
          @click="handleSave"
          :disabled="configStore.isLoading"
          :style="{
            padding: '10px 20px',
            fontSize: '14px',
            fontWeight: '500',
            color: 'white',
            backgroundColor: 'var(--color-accent)',
            border: 'none',
            borderRadius: '6px',
            cursor: configStore.isLoading ? 'not-allowed' : 'pointer',
            opacity: configStore.isLoading ? '0.6' : '1'
          }"
        >
          {{ configStore.isLoading ? 'Saving…' : 'Save' }}
        </button>
      </div>
    </div>
  </div>
</template>
