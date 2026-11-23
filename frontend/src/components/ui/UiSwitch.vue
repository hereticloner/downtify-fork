<template>
  <label
    class="flex cursor-pointer items-start gap-3.5"
    :class="disabled ? 'cursor-not-allowed opacity-50' : ''"
  >
    <span class="min-w-0 flex-1" v-if="label || description || $slots.default">
      <span class="block text-sm font-semibold text-fg">{{ label }}</span>
      <span v-if="description" class="mt-0.5 block text-[13px] text-muted">
        {{ description }}
      </span>
      <slot />
    </span>
    <input
      type="checkbox"
      role="switch"
      class="peer sr-only"
      :aria-label="ariaLabel || undefined"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.checked)"
    />
    <!-- A 24px square, not a pill: ON is an inverted block with an accent
         tick, OFF is an empty 2px frame. No sliding, no transform. -->
    <span
      class="mt-0.5 flex size-6 shrink-0 items-center justify-center border-2 transition-colors duration-100 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent"
      :class="
        modelValue
          ? 'border-line bg-invert text-accent'
          : 'border-line-2 bg-transparent hover:border-line'
      "
      aria-hidden="true"
    >
      <Transition name="fade">
        <AppIcon v-if="modelValue" name="check" :size="14" stroke-width="3" />
      </Transition>
    </span>
  </label>
</template>

<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: String, default: '' },
  description: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  // Names the control when there is no visible `label`.
  ariaLabel: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
