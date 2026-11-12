<template>
  <div class="flex flex-col gap-4">
    <div class="border-2 border-line bg-surface-2 p-3">
      <UiSwitch
        v-model="state.createPlaylist"
        class="flex-row-reverse"
        :label="t('link.createPlaylist')"
        :description="t('link.createPlaylistHint')"
      />
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <UiChips
        :model-value="state.allSelected ? 'all' : ''"
        :items="state.selectionChips"
        @update:model-value="state.onSelectionChip"
      />
      <span class="ml-auto flex items-center gap-2">
        <span class="mono text-muted">{{
          t('library.selectedCount', { count: state.selected.size })
        }}</span>
        <UiButton
          v-if="state.selected.size"
          size="sm"
          variant="primary"
          icon="download"
          @click="state.download(state.selectedSongs)"
        >
          {{ t('link.downloadSelected') }}
        </UiButton>
      </span>
    </div>

    <ol class="flex flex-col border-2 border-line">
      <li
        v-for="row in state.rows"
        :key="row.key"
        class="relative flex h-14 items-center gap-3 border-b border-line-2 px-3 transition-colors duration-100 last:border-b-0"
        :class="
          state.selected.has(row.key) ? 'bg-surface-2' : 'hover:bg-surface-2'
        "
      >
        <span
          v-if="state.selected.has(row.key)"
          class="absolute inset-y-0 left-0 w-1 bg-accent"
          aria-hidden="true"
        />
        <button
          type="button"
          role="checkbox"
          :aria-checked="state.selected.has(row.key)"
          :aria-label="t('library.selectTrack', { title: row.song.name })"
          class="flex size-4 shrink-0 items-center justify-center border-2 transition-colors duration-100"
          :class="
            state.selected.has(row.key)
              ? 'border-line bg-invert text-on-invert'
              : 'border-line-3 hover:border-line'
          "
          @click="state.toggle(row.key)"
        >
          <AppIcon
            v-if="state.selected.has(row.key)"
            name="check"
            :size="11"
            stroke-width="3"
          />
        </button>
        <SongPlayCell :song="row.song" :index="row.index" :queue="playQueue" />
        <CoverArt
          :src="row.song.cover_url"
          :name="row.song.album_name || row.song.name"
          :letter-size="14"
          class="size-10"
        />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-semibold">
            {{ row.song.name }}
          </p>
          <p class="truncate text-[13px] text-muted">
            {{ (row.song.artists || []).join(', ') || row.song.artist }}
          </p>
        </div>
        <span class="hidden w-[26%] truncate text-[13px] text-muted lg:block">{{
          row.song.album_name
        }}</span>
        <span class="mono tabular hidden w-12 text-right text-muted sm:block">
          {{ row.song.duration ? formatDuration(row.song.duration) : '' }}
        </span>
        <div
          v-if="state.hasPlays"
          class="hidden w-40 shrink-0 justify-end md:flex"
        >
          <UiBadge
            v-if="row.song.play_count"
            :tone="playsBadge(row.song).tone"
            icon="eye"
            class="tabular"
            :title="t(playsBadge(row.song).title)"
          >
            {{ formatPlayCount(row.song.play_count, locale) }}
          </UiBadge>
        </div>
        <div class="flex w-28 shrink-0 justify-end">
          <DownloadState :song="row.song" />
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup>
// An artist's top songs as a selectable, downloadable list - one component
// for the pasted-link page (TopSongsView) and the artist page's Top songs
// tab. `state` is what `useTopSongs` returns; it owns every bit of state
// (selection, the playlist switch, the download), this only draws it.
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiChips from '../ui/UiChips.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import DownloadState from '../search/DownloadState.vue'
import SongPlayCell from './SongPlayCell.vue'
import { computed } from 'vue'
import { useLibrary } from '/src/model/library'
import { formatDuration, formatPlayCount } from '/src/lib/format'
import { playableQueue, playsBadge } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const props = defineProps({
  state: { type: Object, required: true },
})

const { t, locale } = useI18n()
const library = useLibrary()

// A downloaded song plays with the list's other downloaded ones queued
// after it, in ranking order; the rest play their preview clip.
const playQueue = computed(() =>
  playableQueue(
    props.state.rows.map((row) => row.song),
    library.findTrack
  )
)
</script>
