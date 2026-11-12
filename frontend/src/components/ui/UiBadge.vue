<template>
  <span
    class="inline-flex h-[20px] shrink-0 items-center gap-1.5 border px-1.5 font-label text-[10px] font-semibold tracking-[0.06em] whitespace-nowrap uppercase"
    :class="toneClass"
  >
    <AppIcon v-if="icon" :name="icon" :size="12" stroke-width="2.4" />
    <slot />
  </span>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  tone: { type: String, default: 'neutral' },
  icon: { type: String, default: '' },
})

// Tone is carried by the frame and the type, never by a fill.
const toneClass = computed(
  () =>
    ({
      accent: 'border-accent text-accent',
      warn: 'border-warn text-warn',
      danger: 'border-danger text-danger',
      neutral: 'border-line-3 text-muted',
      spotify: 'border-spotify text-spotify',
      ytm: 'border-src-ytm text-src-ytm',
    })[props.tone]
)
</script>
