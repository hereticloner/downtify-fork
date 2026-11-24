<template>
  <section
    class="grid border-b-2 border-line sm:grid-cols-[96px_minmax(0,1fr)_auto]"
  >
    <CoverArt
      :src="item.track.cover"
      :name="item.track.album || item.track.title"
      :letter-size="12"
      class="aspect-square border-r-2 border-line"
    />
    <div class="min-w-0 border-b-2 border-line p-3 sm:border-r-2 sm:border-b-0">
      <div class="eyebrow text-faint">{{ t('home.resumeTitle') }}</div>
      <h2 class="mt-1 truncate text-[15px] font-semibold">
        {{ item.track.title || item.track.file }}
      </h2>
      <p class="mono mt-1 truncate text-muted">
        {{ item.track.artist || '' }}
      </p>
      <UiProgress
        class="mt-3"
        :value="progress"
        :aria-label="t('home.resumeTitle')"
      />
      <div class="mono mt-1.5 flex justify-between text-faint">
        <span>{{ formatDuration(item.position) }}</span>
        <span v-if="item.duration">{{ formatDuration(item.duration) }}</span>
      </div>
      <p class="mono mt-2 text-faint">
        {{
          t('home.resumeOnDevice', {
            device: item.device_id ? item.device_id.slice(0, 8) : '—',
          })
        }}
      </p>
    </div>
    <div class="flex items-stretch p-2">
      <UiButton icon="play" class="self-center" @click="$emit('resume')">
        {{ t('home.resumeAction') }}
      </UiButton>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'
import { formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const props = defineProps({ item: { type: Object, required: true } })
defineEmits(['resume', 'dismiss'])

const { t } = useI18n()
const progress = computed(() => {
  const duration = Number(props.item.duration) || 0
  const position = Number(props.item.position) || 0
  return duration > 0 ? Math.min(100, (position / duration) * 100) : 0
})
</script>
