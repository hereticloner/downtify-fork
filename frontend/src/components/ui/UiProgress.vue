<template>
  <!-- Segmented meter: 24 separate rectangles, 2px apart. Completed blocks
       are ink, the block at the playhead is accent, the rest are empty
       frames. No rounded track, no glow. -->
  <div
    class="flex w-full items-stretch gap-0.5"
    :class="[track, indeterminate ? 'animate-pulse' : '']"
    :style="{ height: `${height}px` }"
    role="progressbar"
    :aria-valuenow="indeterminate ? undefined : Math.round(value)"
    aria-valuemin="0"
    aria-valuemax="100"
  >
    <span
      v-for="(state, index) in cells"
      :key="index"
      class="min-w-0 flex-1 transition-colors duration-100"
      :class="stateClass(state)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  indeterminate: { type: Boolean, default: false },
  height: { type: Number, default: 4 },
  color: { type: String, default: '' },
  track: { type: String, default: '' },
})

const SEGMENTS = 24

const cells = computed(() => {
  if (props.indeterminate) return Array.from({ length: SEGMENTS }, () => 'idle')
  const pct = Math.max(0, Math.min(100, props.value))
  const filled = Math.round((pct / 100) * SEGMENTS)
  return Array.from({ length: SEGMENTS }, (_, index) => {
    if (index < filled - 1) return 'done'
    if (index === filled - 1 && filled > 0 && filled < SEGMENTS)
      return 'playhead'
    if (index < filled) return 'done'
    return 'idle'
  })
})

function stateClass(state) {
  if (state === 'done') return props.color || 'bg-fg'
  if (state === 'playhead') return 'bg-accent'
  return props.indeterminate
    ? 'border border-line-2 bg-surface-2'
    : 'border border-line-2'
}
</script>
