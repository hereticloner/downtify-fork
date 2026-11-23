<template>
  <component
    :is="tag"
    v-bind="linkAttrs"
    :type="tag === 'button' ? type : undefined"
    :disabled="tag === 'button' ? disabled || loading : undefined"
    :aria-disabled="disabled || loading || undefined"
    class="eyebrow inline-flex shrink-0 items-center justify-center gap-2 border-2 whitespace-nowrap transition-colors duration-100 disabled:cursor-not-allowed disabled:border-line-2 disabled:bg-transparent disabled:text-faint"
    :class="[sizeClass, variantClass]"
  >
    <span
      v-if="loading"
      class="size-2.5 shrink-0 animate-pulse bg-current"
      aria-hidden="true"
    />
    <AppIcon v-else-if="icon" :name="icon" :size="iconSize" stroke-width="2" />
    <slot />
    <AppIcon
      v-if="iconRight"
      :name="iconRight"
      :size="iconSize"
      stroke-width="2"
    />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  variant: { type: String, default: 'secondary' },
  size: { type: String, default: 'md' },
  icon: { type: String, default: '' },
  iconRight: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  to: { type: [String, Object], default: null },
  href: { type: String, default: '' },
  type: { type: String, default: 'button' },
})

const tag = computed(() => {
  if (props.to) return RouterLink
  if (props.href) return 'a'
  return 'button'
})

const linkAttrs = computed(() => {
  if (props.to) return { to: props.to }
  if (props.href) return { href: props.href, target: '_blank', rel: 'noopener' }
  return {}
})

// Labels are small apparatus type: 10-12px, uppercase, letter-spaced.
// Sizes only control the block's height and padding.
const sizeClass = computed(
  () =>
    ({
      sm: 'h-8 px-3 text-[10px]',
      md: 'h-10 px-4 text-[11px]',
      lg: 'h-12 px-5 text-[12px]',
    })[props.size] || 'h-10 px-4 text-[11px]'
)

const iconSize = computed(() => (props.size === 'sm' ? 14 : 16))

const variantClass = computed(
  () =>
    ({
      primary:
        'play-glow border-line bg-invert text-on-invert hover:bg-fg-3 active:bg-surface active:text-fg',
      secondary:
        'border-line bg-transparent text-fg hover:bg-surface-2 active:bg-raised',
      ghost:
        'border-transparent bg-transparent text-fg-3 hover:bg-surface-2 hover:text-fg active:bg-raised active:text-fg',
      danger:
        'border-danger bg-transparent text-danger hover:bg-surface-2 active:bg-raised',
      invert:
        'border-invert bg-invert text-on-invert hover:bg-fg-3 active:bg-surface active:text-fg',
      // Solid block for controls sitting on a photo (e.g. an artist
      // banner), where a transparent button reads poorly.
      photo: 'border-line bg-glass text-fg hover:bg-surface-2 active:bg-raised',
      plain:
        'border-transparent bg-transparent text-muted hover:bg-surface-2 hover:text-fg active:bg-raised active:text-fg',
    })[props.variant]
)
</script>
