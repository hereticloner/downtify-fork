<template>
  <span
    tabindex="0"
    role="note"
    :title="t('settings.experimentalHint')"
    :aria-label="`${t('settings.experimental')}: ${t('settings.experimentalHint')}`"
    class="mono inline-flex h-[22px] shrink-0 items-center gap-1.5 border border-dashed border-line-3 px-1.5 text-[10px] tracking-[0.06em] whitespace-nowrap text-muted uppercase"
  >
    <AppIcon name="wand" :size="11" />
    {{ t('settings.experimental') }}
  </span>
</template>

<script setup>
// Marks a feature that is still being built. Hovering it - or focusing it
// with the keyboard - explains what that means for the user; the badge
// alone only says "experimental".
import AppIcon from './AppIcon.vue'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
</script>
