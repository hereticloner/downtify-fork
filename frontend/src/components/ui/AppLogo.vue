<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 28 28"
    class="shrink-0"
    role="img"
    aria-label="Downtify"
  >
    <rect
      x="1"
      y="1"
      width="26"
      height="26"
      class="fill-none stroke-fg stroke-2"
    />
    <rect x="7" y="10" width="3" height="8" class="fill-fg" />
    <rect x="12.5" y="6" width="3" height="16" class="fill-accent" />
    <rect x="18" y="9" width="3" height="10" class="fill-fg" />
  </svg>
</template>

<script setup>
defineProps({ size: { type: Number, default: 28 } })
</script>
