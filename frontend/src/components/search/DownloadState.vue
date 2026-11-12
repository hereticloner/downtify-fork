<template>
  <UiBadge v-if="state === 'library'" tone="accent" icon="check">
    {{ t('search.inLibrary') }}
  </UiBadge>
  <UiBadge v-else-if="state === 'done'" tone="accent" icon="check">
    {{ t('queue.statusDone') }}
  </UiBadge>
  <UiBadge v-else-if="state === 'queued'" tone="neutral">
    {{ t('queue.statusQueued') }}
  </UiBadge>
  <div v-else-if="state === 'active'" class="flex w-24 items-center gap-2">
    <UiProgress :value="item.progress" :indeterminate="!item.progress" />
    <span class="mono tabular w-8 text-right text-muted">{{
      item.progress ? `${Math.round(item.progress)}%` : ''
    }}</span>
  </div>
  <button
    v-else
    type="button"
    class="flex size-8 shrink-0 items-center justify-center border-2 transition-colors duration-100"
    :class="
      state === 'failed'
        ? 'border-danger text-danger hover:bg-surface-2'
        : 'border-line-2 text-muted hover:border-line hover:bg-invert hover:text-on-invert'
    "
    :title="state === 'failed' ? t('queue.retry') : t('actions.download')"
    :aria-label="
      state === 'failed'
        ? t('queue.retry')
        : t('actions.downloadItem', { name: song.name })
    "
    @click="download"
  >
    <AppIcon
      :name="state === 'failed' ? 'retry' : 'download'"
      :size="15"
      stroke-width="2"
    />
  </button>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiProgress from '../ui/UiProgress.vue'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useI18n } from '/src/i18n'

const props = defineProps({ song: { type: Object, required: true } })

const { t } = useI18n()
const tracker = useProgressTracker()
const dm = useDownloadManager()
const library = useLibrary()

const item = computed(() => {
  tracker.queueVersion.value
  return tracker.getBySong(props.song)
})

const state = computed(() => {
  if (item.value) return item.value.state
  const artist = (props.song.artists || [])[0] || props.song.artist
  return library.hasSong(artist, props.song.name) ? 'library' : 'new'
})

function download() {
  if (state.value === 'failed') dm.retry(props.song)
  else dm.queue(props.song)
}
</script>
