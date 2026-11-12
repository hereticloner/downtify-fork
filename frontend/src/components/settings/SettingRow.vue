<template>
  <!-- One setting: apparatus label, one line of explanation, and the
       control at the end of the row. -->
  <div
    class="flex flex-col gap-3 px-4 py-3.5"
    :class="
      stacked
        ? 'sm:flex-col sm:items-stretch'
        : 'sm:flex-row sm:items-center sm:justify-between sm:gap-6'
    "
  >
    <div class="min-w-0" :class="stacked ? '' : 'sm:max-w-[58%]'">
      <p class="eyebrow text-fg">{{ label }}</p>
      <p
        v-if="description"
        class="mt-1 text-[12px] leading-relaxed text-pretty text-muted"
      >
        {{ description }}
      </p>
    </div>
    <div
      class="flex min-w-0 flex-wrap items-center gap-2"
      :class="stacked ? '' : 'sm:justify-end'"
    >
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  description: { type: String, default: '' },
  stacked: { type: Boolean, default: false },
})
</script>
