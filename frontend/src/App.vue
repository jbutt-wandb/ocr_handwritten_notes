<script setup>
import { useThemeStore } from './stores/theme'

const themeStore = useThemeStore()
</script>

<template>
  <div style="min-height: 100vh; background-color: var(--color-bg);">
    <header style="border-bottom: 1px solid var(--color-border); background-color: var(--color-surface);">
      <div style="padding: 16px 24px; text-align: center;">
        <h1 style="font-size: 36px; font-weight: 800; color: var(--color-text-primary); letter-spacing: -0.5px;">
          Likho
        </h1>
      </div>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>
