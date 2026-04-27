<script setup>
defineProps({
  image: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['remove'])
</script>

<template>
  <div style="position: relative;">
    <!-- Image -->
    <div
      style="aspect-ratio: 4/3; border-radius: 8px; overflow: hidden; background-color: var(--color-surface); border: 1px solid var(--color-border);"
    >
      <img
        :src="image.preview"
        :alt="image.filename"
        style="width: 100%; height: 100%; object-fit: cover;"
      />
    </div>

    <!-- Remove button (always visible) -->
    <button
      @click.stop="emit('remove', image.id)"
      style="position: absolute; top: 8px; right: 8px; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background-color: rgba(0, 0, 0, 0.6); color: white; border: none; cursor: pointer;"
      @mouseenter="$event.target.style.backgroundColor = '#ef4444'"
      @mouseleave="$event.target.style.backgroundColor = 'rgba(0, 0, 0, 0.6)'"
      aria-label="Remove image"
    >
      <svg style="width: 12px; height: 12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>

    <!-- Filename -->
    <p
      style="margin-top: 6px; font-size: 12px; color: var(--color-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
      :title="image.filename"
    >
      {{ image.filename }}
    </p>
  </div>
</template>
