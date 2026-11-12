<template>
  <section
    class="border-2 border-line bg-surface"
    :class="padded ? 'p-5 sm:p-6' : ''"
  >
    <header
      v-if="title || $slots.actions"
      class="mb-4 flex items-start justify-between gap-4 border-b border-line-2 pb-2"
    >
      <div class="min-w-0">
        <h2 class="eyebrow text-fg">{{ title }}</h2>
        <p v-if="description" class="mt-1 text-[13px] text-pretty text-muted">
          {{ description }}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
      </div>
    </header>
    <slot />
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  padded: { type: Boolean, default: true },
})
</script>
