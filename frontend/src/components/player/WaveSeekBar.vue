<template>
  <!-- Seek bar as a segmented meter: 24 blocks, 2px apart, the block under
       the playhead in accent. Dense ink, no waveform, no glow. The fill
       follows `currentColor`, so the same bar works on paper (transport,
       dark) and inside the inverted bar. -->
  <div
    ref="track"
    role="slider"
    tabindex="0"
    :aria-label="label"
    :aria-valuemin="0"
    :aria-valuemax="max"
    :aria-valuenow="Math.round(modelValue)"
    :aria-valuetext="valueText"
    class="group relative flex w-full cursor-pointer touch-none items-center py-1 outline-none"
    @pointerdown="onDown"
    @keydown="onKey"
  >
    <div class="flex w-full items-stretch gap-0.5" aria-hidden="true">
      <span
        v-for="(cell, index) in cells"
        :key="index"
        class="h-1 min-w-0 flex-1 border transition-colors duration-100 md:h-2"
        :class="cellClass(cell)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSlider } from './useSlider'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 5 },
  label: { type: String, default: '' },
  valueText: { type: String, default: undefined },
  playing: { type: Boolean, default: false },
  // { primary, secondary, soft } from useCoverPalette, or null. Kept in
  // the signature for callers; the language has one accent, so the meter
  // no longer recolours itself from the artwork.
  palette: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'commit'])

const { track, percent, onDown, onKey } = useSlider(props, emit)

const SEGMENTS = 24

const cells = computed(() => {
  const filled = Math.round((percent.value / 100) * SEGMENTS)
  return Array.from({ length: SEGMENTS }, (_, index) => {
    if (index < filled - 1) return 'done'
    if (index === filled - 1 && filled > 0 && filled < SEGMENTS)
      return 'playhead'
    if (index < filled) return 'done'
    return 'idle'
  })
})

function cellClass(cell) {
  if (cell === 'done') return 'border-transparent bg-current'
  if (cell === 'playhead') return 'border-transparent bg-accent'
  return 'border-line-2 bg-transparent'
}
</script>
