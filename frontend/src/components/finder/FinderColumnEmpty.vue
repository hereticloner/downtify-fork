<template>
  <div
    class="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-12 text-center"
  >
    <span
      class="flex size-10 items-center justify-center border-2 border-line-2 text-muted"
    >
      <AppIcon :name="icon" :size="18" />
    </span>
    <div class="flex max-w-xs flex-col gap-1.5">
      <p class="eyebrow text-fg">{{ title }}</p>
      <p v-if="body" class="text-[13px] text-pretty text-muted">{{ body }}</p>
    </div>
    <div v-if="$slots.default" class="mt-1 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup>
// UiEmpty's message, without its dashed frame: a Finder column is already
// framed, so a nothing-here/failed message just fills it, centred.
import AppIcon from '../ui/AppIcon.vue'

defineProps({
  icon: { type: String, default: 'music' },
  title: { type: String, required: true },
  body: { type: String, default: '' },
})
</script>
