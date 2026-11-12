<template>
  <section class="min-w-0 border-2 border-line bg-surface">
    <!-- Group header: an apparatus strip, inverted when the block is
         destructive so it never reads as a setting. -->
    <header
      v-if="title"
      class="border-b-2 border-line"
      :class="danger ? 'bg-invert text-on-invert' : 'bg-surface-2'"
    >
      <div class="flex items-start justify-between gap-4 px-4 py-2.5">
        <div class="min-w-0">
          <h3 class="eyebrow" :class="danger ? 'text-on-invert' : 'text-fg'">
            {{ title }}
          </h3>
          <p
            v-if="description"
            class="mt-1 text-[12px] leading-relaxed text-pretty"
            :class="danger ? 'text-on-invert/70' : 'text-muted'"
          >
            {{ description }}
          </p>
        </div>
        <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
          <slot name="actions" />
        </div>
      </div>
    </header>
    <div class="flex min-w-0 flex-col divide-y divide-line-2">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  // Destructive operations: inverted header strip.
  danger: { type: Boolean, default: false },
})
</script>
