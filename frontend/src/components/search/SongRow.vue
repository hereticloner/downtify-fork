<template>
  <!-- One row of the results table: number, cover, title over its artist,
       album, time, the source it came from, and its download state. -->
  <div
    class="group flex h-14 items-center gap-3 border-b border-line-2 px-3 transition-colors duration-100 last:border-b-0 hover:bg-surface-2"
  >
    <span
      v-if="index !== null"
      class="mono tabular w-6 shrink-0 text-center text-faint max-sm:hidden"
    >
      {{ String(index + 1).padStart(2, '0') }}
    </span>
    <CoverArt
      :src="song.cover_url"
      :name="song.album_name || song.name"
      :letter-size="10"
      :icon-size="13"
      class="size-9"
    />
    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <span class="truncate text-[13px] font-semibold">{{ song.name }}</span>
        <span
          v-if="song.inLibrary"
          class="mono shrink-0 border border-line-2 px-1 text-[9px] leading-[13px] text-accent"
          >{{ t('search.inLibrary') }}</span
        >
        <span
          v-if="song.explicit"
          class="mono shrink-0 border border-line-3 px-1 text-[9px] leading-[13px] text-muted"
          :title="t('search.explicit')"
          >E</span
        >
      </p>
      <p class="mono truncate text-muted">
        {{ artists
        }}<span v-if="song.album_name" class="lg:hidden">
          · {{ song.album_name }}</span
        >
      </p>
    </div>
    <span class="mono hidden w-[26%] truncate text-muted lg:block">{{
      song.album_name
    }}</span>
    <span class="mono tabular hidden w-12 text-right text-muted sm:block">
      {{ song.duration ? formatDuration(song.duration) : '' }}
    </span>
    <a
      v-if="sourceUrl"
      :href="sourceUrl"
      target="_blank"
      rel="noopener"
      class="hidden size-8 shrink-0 items-center justify-center border-2 border-line-2 text-muted transition-colors duration-100 hover:border-line hover:text-fg sm:flex lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100"
      :title="openSourceLabel"
      :aria-label="openSourceLabel"
    >
      <AppIcon name="arrow-up-right" :size="14" />
    </a>
    <div class="flex w-24 shrink-0 justify-end">
      <DownloadState :song="song" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import DownloadState from './DownloadState.vue'
import { formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, default: null },
})
const { t } = useI18n()

const artists = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)
const sourceUrl = computed(() => {
  const url = String(props.song.url || '')
  return /^https?:\/\//.test(url) ? url : ''
})
// Charts' Deezer tracks reuse this row; their link opens Deezer, not
// YouTube Music.
const openSourceLabel = computed(() =>
  props.song.source === 'deezer' ? t('link.openDeezer') : t('search.openSource')
)
</script>
