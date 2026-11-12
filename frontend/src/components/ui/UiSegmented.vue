<template>
  <div
    class="inline-flex h-10 shrink-0 items-stretch border-2 border-line"
    role="radiogroup"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      :aria-checked="option.value === modelValue"
      :title="option.label"
      :aria-label="option.label"
      class="flex min-w-9 items-center justify-center gap-1.5 border-l-2 border-line px-3 transition-colors duration-100 first:border-l-0"
      :class="
        option.value === modelValue
          ? 'bg-invert text-on-invert'
          : 'bg-transparent text-muted hover:bg-surface-2 hover:text-fg'
      "
      @click="$emit('update:modelValue', option.value)"
    >
      <AppIcon v-if="option.icon" :name="option.icon" :size="16" />
      <span v-if="showLabels" class="eyebrow text-current">{{
        option.label
      }}</span>
    </button>
  </div>
</template>

<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  options: { type: Array, required: true },
  modelValue: { type: [String, Number], default: '' },
  showLabels: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>
