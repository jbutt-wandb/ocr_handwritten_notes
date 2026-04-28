<script setup>
import { ref, computed, watch } from 'vue'
import { useConfigStore } from '../stores/config'

const configStore = useConfigStore()

const openaiKey = ref('')
const wandbKey = ref('')
const entity = ref('')
const project = ref('')
const showOpenai = ref(false)
const showWandb = ref(false)
const localError = ref(null)

const isFirstRun = computed(() => configStore.modalMode === 'firstRun')
const status = computed(() => configStore.status)

watch(
  () => configStore.isModalOpen,
  (open) => {
    if (open) {
      openaiKey.value = ''
      wandbKey.value = ''
      entity.value = status.value?.weave_entity || ''
      project.value = status.value?.weave_project || ''
      showOpenai.value = false
      showWandb.value = false
      localError.value = null
    }
  }
)

const wandbFieldsAnyFilled = computed(
  () => !!(wandbKey.value || entity.value || project.value)
)
const wandbFieldsAllFilled = computed(
  () => !!(wandbKey.value && entity.value && project.value)
)

const openaiPlaceholder = computed(() =>
  status.value?.openai_preview ? `current: ${status.value.openai_preview}` : 'sk-...'
)
const wandbPlaceholder = computed(() =>
  status.value?.wandb_preview ? `current: ${status.value.wandb_preview}` : 'WANDB_API_KEY'
)

async function handleSave() {
  localError.value = null

  if (!status.value?.openai_configured && !openaiKey.value.trim()) {
    localError.value = 'OpenAI API key is required'
    return
  }
  if (wandbFieldsAnyFilled.value && !wandbFieldsAllFilled.value) {
    localError.value = 'For W&B tracing, fill in API key, entity, and project (or leave all three blank)'
    return
  }

  const payload = {}
  if (openaiKey.value.trim()) payload.openai_api_key = openaiKey.value.trim()
  if (wandbKey.value.trim()) payload.wandb_api_key = wandbKey.value.trim()
  if (entity.value.trim()) payload.weave_entity = entity.value.trim()
  if (project.value.trim()) payload.weave_project = project.value.trim()

  if (Object.keys(payload).length === 0) {
    configStore.closeModal()
    return
  }

  try {
    await configStore.save(payload)
    configStore.closeModal()
  } catch (err) {
    // error already in store; localError mirrors for visibility
    localError.value = configStore.lastError || err.message
  }
}

function handleSkip() {
  configStore.closeModal({ skip: true })
}

function handleCancel() {
  configStore.closeModal()
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
          ? 'Add your API keys to enable OCR. Stored locally in .likho_config.json.'
          : 'Update API keys. Existing values stay unless you enter new ones.' }}
      </p>

      <!-- OpenAI -->
      <div style="margin-bottom: 18px;">
        <label style="display: block; font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 6px;">
          OpenAI API Key <span style="color: #f87171;">*</span>
          <span v-if="status?.openai_configured" style="font-weight: 400; color: var(--color-text-muted); margin-left: 6px;">
            ({{ status.openai_preview }} from {{ status.openai_source }})
          </span>
        </label>
        <div style="display: flex; gap: 8px;">
          <input
            :type="showOpenai ? 'text' : 'password'"
            v-model="openaiKey"
            :placeholder="openaiPlaceholder"
            autocomplete="off"
            spellcheck="false"
            style="flex: 1; padding: 10px 12px; font-size: 14px; font-family: ui-monospace, monospace; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none;"
          />
          <button
            type="button"
            @click="showOpenai = !showOpenai"
            style="padding: 0 12px; font-size: 12px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
          >
            {{ showOpenai ? 'Hide' : 'Show' }}
          </button>
        </div>
      </div>

      <!-- W&B section -->
      <div style="margin-top: 24px; padding-top: 18px; border-top: 1px dashed var(--color-border);">
        <p style="font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin: 0 0 4px 0;">
          Weights & Biases (optional)
        </p>
        <p style="font-size: 12px; color: var(--color-text-muted); margin: 0 0 14px 0;">
          Adds Weave tracing for OCR calls. Provide all three or leave all blank.
        </p>

        <label style="display: block; font-size: 13px; color: var(--color-text-primary); margin-bottom: 6px;">
          W&B API Key
          <span v-if="status?.wandb_configured" style="font-weight: 400; color: var(--color-text-muted); margin-left: 6px;">
            ({{ status.wandb_preview }} from {{ status.wandb_source }})
          </span>
        </label>
        <div style="display: flex; gap: 8px; margin-bottom: 12px;">
          <input
            :type="showWandb ? 'text' : 'password'"
            v-model="wandbKey"
            :placeholder="wandbPlaceholder"
            autocomplete="off"
            spellcheck="false"
            style="flex: 1; padding: 10px 12px; font-size: 14px; font-family: ui-monospace, monospace; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none;"
          />
          <button
            type="button"
            @click="showWandb = !showWandb"
            style="padding: 0 12px; font-size: 12px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer;"
          >
            {{ showWandb ? 'Hide' : 'Show' }}
          </button>
        </div>

        <label style="display: block; font-size: 13px; color: var(--color-text-primary); margin-bottom: 6px;">Entity</label>
        <input
          v-model="entity"
          placeholder="your-wandb-entity"
          autocomplete="off"
          style="width: 100%; padding: 10px 12px; margin-bottom: 12px; font-size: 14px; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none; box-sizing: border-box;"
        />

        <label style="display: block; font-size: 13px; color: var(--color-text-primary); margin-bottom: 6px;">Project</label>
        <input
          v-model="project"
          placeholder="likho"
          autocomplete="off"
          style="width: 100%; padding: 10px 12px; font-size: 14px; background-color: var(--color-bg); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; outline: none; box-sizing: border-box;"
        />
      </div>

      <!-- Errors / warnings -->
      <div v-if="localError" style="margin-top: 16px; padding: 10px 12px; border-radius: 6px; font-size: 13px; background-color: rgba(239, 68, 68, 0.1); color: #f87171;">
        {{ localError }}
      </div>
      <div v-else-if="configStore.lastWeaveWarning" style="margin-top: 16px; padding: 10px 12px; border-radius: 6px; font-size: 13px; background-color: rgba(245, 158, 11, 0.12); color: #fbbf24;">
        Saved, but Weave init warning: {{ configStore.lastWeaveWarning }}
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
