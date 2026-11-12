<template>
  <!-- Page masthead: sentence-case display title, apparatus label under it,
       and the page's action blocks on the right. No frame of its own - the
       view decides where the structural rule falls. -->
  <div
    class="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-end sm:justify-between sm:gap-6 sm:px-6 sm:py-5"
  >
    <div class="min-w-0">
      <h1
        class="text-display text-[26px] leading-[1.05] font-bold tracking-[-0.02em] sm:text-[34px]"
      >
        {{ title }}
      </h1>
      <p v-if="subtitle" class="eyebrow mt-2 truncate">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap items-center gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>
