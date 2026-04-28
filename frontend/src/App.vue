<script setup>
import { onMounted } from 'vue'
import { useThemeStore } from './stores/theme'
import { useConfigStore } from './stores/config'
import CredentialsModal from './components/CredentialsModal.vue'

const themeStore = useThemeStore()
const configStore = useConfigStore()

onMounted(async () => {
  try {
    await configStore.fetchStatus()
    if (!configStore.openaiConfigured) {
      configStore.openModal('firstRun')
    }
  } catch (err) {
    console.error('Could not fetch config status:', err)
  }
})

function openSettings() {
  configStore.openModal('edit')
}
</script>

<template>
  <div style="min-height: 100vh; background-color: var(--color-bg);">
    <header style="border-bottom: 1px solid var(--color-border); background-color: var(--color-surface); position: relative;">
      <div style="padding: 16px 24px; text-align: center;">
        <h1 style="font-size: 36px; font-weight: 800; color: var(--color-text-primary); letter-spacing: -0.5px;">
          Likho
        </h1>
      </div>
      <button
        @click="openSettings"
        aria-label="Settings"
        title="Credentials"
        style="position: absolute; top: 50%; right: 24px; transform: translateY(-50%); background: transparent; border: 1px solid var(--color-border); color: var(--color-text-muted); width: 56px; height: 56px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;"
        @mouseenter="$event.currentTarget.style.backgroundColor = 'var(--color-surface-hover)'"
        @mouseleave="$event.currentTarget.style.backgroundColor = 'transparent'"
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
      </button>
    </header>
    <main>
      <router-view />
    </main>
    <CredentialsModal />
  </div>
</template>
