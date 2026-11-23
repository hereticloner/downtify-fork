<template>
  <div
    class="animate-rise flex flex-col items-center justify-center gap-3 border-2 border-dashed border-line px-6 py-14 text-center"
  >
    <span
      class="flex size-12 items-center justify-center border border-line-2 bg-surface-2 text-muted"
    >
      <AppIcon :name="icon" :size="22" />
    </span>
    <div class="flex max-w-sm flex-col gap-1.5">
      <p class="eyebrow text-fg">{{ title }}</p>
      <p v-if="body" class="text-[13px] text-pretty text-muted">{{ body }}</p>
    </div>
    <div v-if="$slots.default" class="mt-2 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  icon: { type: String, default: 'music' },
  title: { type: String, required: true },
  body: { type: String, default: '' },
})
</script>
