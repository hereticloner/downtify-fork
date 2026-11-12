<template>
  <div class="flex min-w-0 flex-col items-center gap-2 select-none">
    <span
      class="mono tabular h-4 leading-4 transition-opacity"
      :class="
        dragging || modelValue !== 0
          ? 'text-fg-2'
          : 'text-transparent group-hover/eq:text-faint'
      "
      aria-hidden="true"
      >{{ shortValue }}</span
    >
    <div
      ref="track"
      role="slider"
      tabindex="0"
      aria-orientation="vertical"
      :aria-label="label"
      :aria-valuemin="-limit"
      :aria-valuemax="limit"
      :aria-valuenow="modelValue"
      :aria-valuetext="formatGain(modelValue)"
      class="group relative flex w-6 cursor-pointer touch-none justify-center outline-none"
      :style="{ height: `${height}px` }"
      @pointerdown="onDown"
      @keydown="onKey"
      @dblclick="reset"
    >
      <!-- Track -->
      <span class="absolute inset-y-0 w-1 bg-raised" aria-hidden="true" />
      <!-- 0 dB mark -->
      <span
        class="absolute top-1/2 h-px w-3 -translate-y-1/2 bg-line-3"
        aria-hidden="true"
      />
      <!-- Fill from 0 dB to the value -->
      <span class="absolute w-1" :style="fillStyle" aria-hidden="true" />
      <span
        class="absolute left-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 border border-line bg-fg"
        :style="{ top: `${100 - percent}%` }"
        aria-hidden="true"
      />
    </div>
    <span
      class="mono whitespace-nowrap tabular text-faint"
      aria-hidden="true"
      >{{ caption }}</span
    >
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSlider } from './useSlider'
import { formatGain, GAIN_STEP } from '/src/lib/equalizer'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  limit: { type: Number, required: true },
  label: { type: String, required: true },
  caption: { type: String, required: true },
  // A colour or `currentColor`; the band fill follows the slider's ink.
  color: { type: String, default: 'currentColor' },
  height: { type: Number, default: 180 },
})
const emit = defineEmits(['update:modelValue', 'commit'])

const { track, dragging, percent, onDown, onKey } = useSlider(
  {
    get modelValue() {
      return props.modelValue
    },
    get min() {
      return -props.limit
    },
    get max() {
      return props.limit
    },
    step: GAIN_STEP,
  },
  emit,
  { vertical: true, snap: true }
)

const shortValue = computed(() => {
  const v = Math.round(props.modelValue * 10) / 10
  return v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0'
})

const fillStyle = computed(() => {
  const top = Math.min(50, 100 - percent.value)
  const bottom = Math.min(50, percent.value)
  return {
    top: `${top}%`,
    bottom: `${bottom}%`,
    backgroundColor: props.color,
  }
})

function reset() {
  emit('update:modelValue', 0)
  emit('commit', 0)
}
</script>
