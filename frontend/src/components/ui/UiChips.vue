<template>
  <!-- A row of square blocks: each chip is a 1px frame, the selected one
       inverts. Gaps are 2px so the row reads as a ruled strip. -->
  <div
    class="flex items-stretch gap-0.5 overflow-x-auto border-y-2 border-line py-0.5 [scrollbar-width:none]"
  >
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="eyebrow inline-flex h-7 shrink-0 items-center gap-2 border px-3 whitespace-nowrap transition-colors duration-100"
      :class="
        item.id === modelValue
          ? 'play-glow border-line bg-invert text-on-invert'
          : 'border-line-2 bg-transparent text-muted hover:border-line hover:text-fg'
      "
      :aria-pressed="item.id === modelValue"
      @click="$emit('update:modelValue', item.id)"
    >
      {{ item.label }}
      <span
        v-if="item.count !== undefined && item.count !== null"
        class="mono"
        >{{ item.count }}</span
      >
    </button>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
