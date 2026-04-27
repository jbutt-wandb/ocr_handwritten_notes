<script setup>
import { ref } from 'vue'

const emit = defineEmits(['files-selected'])

const isDragging = ref(false)
const fileInput = ref(null)

const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

function handleDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(e) {
  e.preventDefault()
  isDragging.value = false

  const files = Array.from(e.dataTransfer.files).filter(
    file => allowedTypes.includes(file.type)
  )

  if (files.length > 0) {
    emit('files-selected', files)
  }
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files)
  if (files.length > 0) {
    emit('files-selected', files)
  }
  e.target.value = ''
}

function openFilePicker() {
  fileInput.value?.click()
}
</script>

<template>
  <div
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
    @click="openFilePicker"
    style="border: 2px dashed var(--color-border); border-radius: 12px; padding: 60px 32px; text-align: center; cursor: pointer; transition: all 0.2s ease;"
    :style="{
      borderColor: isDragging ? 'var(--color-accent)' : 'var(--color-border)',
      backgroundColor: isDragging ? 'var(--color-accent-muted)' : 'transparent'
    }"
  >
    <input
      ref="fileInput"
      type="file"
      multiple
      accept="image/jpeg,image/png,image/gif,image/webp"
      style="display: none;"
      @change="handleFileSelect"
    />

    <div style="display: flex; flex-direction: column; align-items: center; gap: 16px;">
      <!-- Icon with explicit size -->
      <svg
        style="width: 48px; height: 48px;"
        :style="{ color: isDragging ? 'var(--color-accent)' : 'var(--color-text-muted)' }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.5"
          d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
        />
      </svg>

      <!-- Text -->
      <div>
        <p style="font-size: 16px; font-weight: 500; color: var(--color-text-primary);">
          Drop images here or click to browse
        </p>
        <p style="margin-top: 8px; font-size: 14px; color: var(--color-text-muted);">
          JPG, PNG, GIF, WebP
        </p>
      </div>
    </div>
  </div>
</template>
