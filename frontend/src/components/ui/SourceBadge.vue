<template>
  <span
    v-if="meta"
    class="mono inline-flex h-[22px] shrink-0 items-center gap-1.5 border border-line-2 text-[10px] tracking-[0.06em] whitespace-nowrap text-muted uppercase"
    :class="compact ? 'w-[22px] justify-center' : 'px-1.5'"
    :title="t('source.from', { source: meta.label })"
  >
    <AppIcon :name="meta.icon" :size="11" />
    <span v-if="!compact">{{ meta.label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  source: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
const { t } = useI18n()

// The audio source a track was downloaded from (backend job `provider`).
// Monochrome on purpose: colour in this language belongs to artwork only.
const SOURCES = {
  'youtube-music': { label: 'YouTube Music', icon: 'youtube' },
  youtube: { label: 'YouTube', icon: 'youtube' },
  slskd: { label: 'slskd', icon: 'share' },
}

const meta = computed(() => SOURCES[props.source] || null)
</script>
