<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to || undefined"
    :type="to ? undefined : 'button'"
    :title="label"
    :aria-label="label"
    :aria-pressed="toggle ? active : undefined"
    :disabled="to ? undefined : disabled"
    class="inline-flex shrink-0 items-center justify-center border-2 transition-colors duration-100 disabled:cursor-not-allowed disabled:border-line-2 disabled:text-faint"
    :class="[
      sizeClass,
      photo
        ? 'border-line bg-glass text-fg hover:bg-surface-2 active:bg-raised'
        : active
          ? 'border-line bg-invert text-on-invert active:bg-surface active:text-fg'
          : 'border-line-2 text-muted hover:border-line hover:bg-surface-2 hover:text-fg active:bg-raised active:text-fg',
    ]"
  >
    <AppIcon :name="icon" :size="iconSize" />
    <slot />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  size: { type: String, default: 'md' },
  active: { type: Boolean, default: false },
  toggle: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  // Solid block, independent of theme - see UiButton's 'photo'
  // variant for why (a control sitting on a banner image).
  photo: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  to: { type: [String, Object], default: null },
})

// Every control is square: the `round` prop is kept for compatibility,
// the language has no circles.
const sizeClass = computed(
  () =>
    ({
      sm: 'size-8',
      md: 'size-10',
      lg: 'size-11',
      touch: 'size-11 lg:size-8',
    })[props.size] || 'size-10'
)
const iconSize = computed(() => ({ sm: 16, md: 18, lg: 20 })[props.size] || 18)
</script>
