<template>
  <span
    class="inline-flex items-end gap-0.5"
    :style="{ height: `${size}px` }"
    aria-hidden="true"
  >
    <span
      v-for="n in 3"
      :key="n"
      class="block w-[3px] origin-bottom bg-accent"
      :class="barClass"
      :style="{ height: `${size}px`, animationDelay: `${-0.3 * (n - 1)}s` }"
    />
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: { type: Number, default: 14 },
  playing: { type: Boolean, default: true },
  // Stepped four-position variant for the compact playing-row indicator.
  stepped: { type: Boolean, default: false },
})

const barClass = computed(() => {
  if (!props.playing) {
    return props.stepped ? 'animate-eq-mini eq-paused' : 'scale-y-[0.35]'
  }
  return props.stepped ? 'animate-eq-mini' : 'animate-eq'
})
</script>
