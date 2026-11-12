<template>
  <div
    v-if="track"
    class="flex h-full min-h-0 flex-col gap-4 overflow-y-auto [scrollbar-width:thin]"
  >
    <!-- Technical sheet: label cell, value cell, 1px rules. -->
    <dl class="border-t border-line-2">
      <div
        v-for="row in rows"
        :key="row.label"
        class="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)] items-baseline gap-3 border-b border-line-2 py-2"
      >
        <dt class="eyebrow">{{ row.label }}</dt>
        <dd class="mono min-w-0 break-words text-fg-2">{{ row.value }}</dd>
      </div>
    </dl>
    <div class="flex flex-wrap gap-2">
      <UiButton
        v-if="track.album"
        variant="secondary"
        size="sm"
        icon="disc"
        :to="{
          name: 'Album',
          query: { artist: track.albumArtist, title: track.album },
        }"
      >
        {{ t('player.goToAlbum') }}
      </UiButton>
      <UiButton
        v-if="track.albumArtist"
        variant="secondary"
        size="sm"
        icon="user"
        :to="{ name: 'Artist', query: { name: track.albumArtist } }"
      >
        {{ t('player.goToArtist') }}
      </UiButton>
      <a
        :href="track.url"
        :download="saveName(track.file)"
        class="eyebrow inline-flex h-8 shrink-0 items-center justify-center gap-2 border-2 border-line bg-transparent px-3 whitespace-nowrap text-fg transition-colors duration-100 hover:bg-surface-2 active:bg-raised"
      >
        <AppIcon name="download" :size="14" stroke-width="2" />
        {{ t('library.saveToDevice') }}
      </a>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import { usePlayer } from '/src/model/player'
import { formatBytes, formatDuration, timeAgo } from '/src/lib/format'
import { saveName } from '/src/lib/paths'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { t, locale } = useI18n()
const track = computed(() => player.currentTrack.value)

const rows = computed(() => {
  const tr = track.value
  if (!tr) return []
  return [
    { label: t('track.title'), value: tr.title },
    { label: t('track.artist'), value: tr.artist },
    { label: t('track.album'), value: tr.album },
    { label: t('track.trackNumber'), value: tr.trackNumber || '' },
    { label: t('track.year'), value: tr.year },
    {
      label: t('track.length'),
      value: tr.duration ? formatDuration(tr.duration) : '',
    },
    { label: t('track.format'), value: tr.format },
    { label: t('track.size'), value: tr.size ? formatBytes(tr.size) : '' },
    {
      label: t('track.added'),
      value: tr.added ? timeAgo(tr.added, locale.value) : '',
    },
    { label: t('track.file'), value: tr.file },
  ].filter((row) => row.value !== '' && row.value !== undefined)
})
</script>
