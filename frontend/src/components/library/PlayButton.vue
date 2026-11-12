<template>
  <button
    type="button"
    class="flex size-12 shrink-0 items-center justify-center border-2 border-line bg-invert text-on-invert transition-colors duration-100 hover:bg-fg-3 active:bg-surface active:text-fg disabled:cursor-not-allowed disabled:border-line-2 disabled:bg-transparent disabled:text-faint"
    :aria-label="playing ? t('player.pause') : label"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <AppIcon :name="playing ? 'pause' : 'play'" :size="18" stroke-width="2" />
  </button>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'

defineProps({
  label: { type: String, default: '' },
  playing: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
defineEmits(['click'])
const { t } = useI18n()
</script>
