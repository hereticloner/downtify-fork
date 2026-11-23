<template>
  <!-- A5 — a quiet four-dot cursor trail. Rendered only for fine pointers
       that allow motion; touch and reduced motion get no element at all. -->
  <div v-if="enabled" class="cursor-trail" aria-hidden="true">
    <span
      v-for="(dot, index) in dots"
      :key="index"
      class="cursor-trail-dot"
      :style="{
        transform: `translate3d(${point.x - dot.size / 2}px, ${point.y - dot.size / 2}px, 0)`,
        transitionDuration: `${dot.duration}ms`,
        opacity: dot.opacity,
        width: `${dot.size}px`,
        height: `${dot.size}px`,
      }"
    />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'

// One query gates both rendering and the transform: no element under reduced
// motion or on touch, so there is no static state to reconcile there.
const QUERY =
  '(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)'

// Each dot lags a little longer and fades a little more than the last.
const dots = [
  { duration: 120, opacity: 0.9, size: 6 },
  { duration: 170, opacity: 0.55, size: 5 },
  { duration: 220, opacity: 0.3, size: 4 },
  { duration: 270, opacity: 0.14, size: 3 },
]

const point = reactive({ x: -100, y: -100 })
const enabled = ref(false)
let mq

function onPointerMove(event) {
  point.x = event.clientX
  point.y = event.clientY
}

function update() {
  enabled.value = mq.matches
}

onMounted(() => {
  mq = window.matchMedia(QUERY)
  update()
  mq.addEventListener('change', update)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
})

onBeforeUnmount(() => {
  mq?.removeEventListener('change', update)
  window.removeEventListener('pointermove', onPointerMove)
})
</script>

<style scoped>
.cursor-trail {
  position: fixed;
  inset: 0;
  z-index: 60;
  overflow: hidden;
  pointer-events: none;
}
.cursor-trail-dot {
  position: absolute;
  top: 0;
  left: 0;
  background-color: var(--c-accent);
}

@media (hover: hover) and (prefers-reduced-motion: no-preference) {
  .cursor-trail-dot {
    transition-property: transform;
    transition-timing-function: linear;
    will-change: transform;
  }
}
</style>
