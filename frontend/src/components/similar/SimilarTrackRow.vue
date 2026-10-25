<template>
  <div
    class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors hover:bg-surface"
  >
    <span
      v-if="index !== null"
      class="tabular w-6 text-center text-[13px] text-faint max-sm:hidden"
    >
      {{ index + 1 }}
    </span>
    <button
      type="button"
      class="relative shrink-0"
      :aria-label="playLabel"
      :disabled="!playable"
      @click.stop="toggle"
    >
      <CoverArt
        :src="song.cover_url"
        :name="song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
      <span
        v-if="playable"
        class="absolute inset-0 hidden items-center justify-center rounded-[8px] bg-black/45 text-white group-hover:flex"
        :class="isCurrent ? '!flex' : ''"
      >
        <AppIcon
          v-if="loading"
          name="refresh"
          :size="16"
          class="animate-spin"
        />
        <AppIcon v-else :name="overlayIcon" :size="16" />
      </span>
    </button>
    <div class="min-w-0 flex-1">
      <p class="truncate text-sm font-semibold">{{ song.name }}</p>
      <p class="truncate text-[13px] text-muted">{{ artistName }}</p>
    </div>
    <span
      v-if="song.album_name"
      class="hidden w-[30%] truncate text-[13px] text-muted lg:block"
      >{{ song.album_name }}</span
    >
    <span
      class="tabular hidden w-12 text-right text-[13px] text-muted sm:block"
    >
      {{ song.duration ? formatDuration(song.duration) : '' }}
    </span>
    <!-- Same grid as every other track row: the wand re-seeds the mix
         from this track, then the download state. Wide enough for the
         wand plus the download's widest state (see TrackDownPlay). -->
    <div class="flex w-40 shrink-0 items-center justify-end gap-2">
      <SimilarButton :artist="firstArtist" :title="song.name" filled />
      <UiBadge v-if="inLibrary" tone="accent" icon="check">
        {{ t('search.inLibrary') }}
      </UiBadge>
      <DownloadState
        v-else-if="resolved || downloadable"
        :song="resolved || song"
      />
      <button
        v-else
        type="button"
        class="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-fg-3 transition-colors hover:bg-accent hover:text-on-accent disabled:opacity-50"
        :title="t('actions.download')"
        :aria-label="t('actions.downloadItem', { name: song.name })"
        :disabled="resolving"
        @click="resolveAndDownload"
      >
        <AppIcon
          :name="resolving ? 'refresh' : 'download'"
          :size="16"
          stroke-width="2"
          :class="resolving ? 'animate-spin' : ''"
        />
      </button>
    </div>
  </div>
</template>

<script setup>
// One similar track: full playback on the cover (from the library, else
// streamed through the built-in player as one row of the whole list - see
// model/stream.js and the player's own stream resolution), and a download
// button straight from its video id. The row hands off to DownloadState, so
// progress, queue and retry look exactly like search results.
//
// Deliberately like the fork's other stream-aware rows, not like the
// preview-based ones: nothing here plays a 30 s clip.
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import DownloadState from '../search/DownloadState.vue'
import SimilarButton from './SimilarButton.vue'
import { formatDuration } from '/src/lib/format'
import API from '/src/model/api'
import { useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { isStreamingSong, songToPlayerTrack } from '/src/model/stream'
import { rowKey, songArtist, songTitle } from '/src/model/streamResolve'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, default: null },
  // The whole song list, for a mixed queue (downloaded rows from the
  // library, the rest streamed) the player works through to the end.
  songs: { type: Array, default: null },
})

const { t } = useI18n()
const player = usePlayer()
const library = useLibrary()
const dm = useDownloadManager()
const actions = useTrackActions()
const ui = useUi()

const resolving = ref(false)
const resolved = ref(null)

const artistName = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)
const firstArtist = computed(
  () => (props.song.artists || [])[0] || props.song.artist || ''
)

// The library track behind the song once it's downloaded - the library
// refreshes itself after a download finishes, and this follows it.
const track = computed(() =>
  library.findTrack(songArtist(props.song), songTitle(props.song))
)
const streaming = computed(() => isStreamingSong(props.song))
const isCurrent = computed(
  () =>
    (!!track.value && player.currentTrack.value?.file === track.value.file) ||
    streaming.value
)
// Resolving the stream URL right now (a direct tap, or the player
// working through the queue): the row spins meanwhile.
const loading = computed(
  () =>
    player.resolving.value != null &&
    rowKey(player.resolving.value) === rowKey(props.song)
)
// A song with an artist or a title always plays: from the library, else
// streamed in full.
const playable = computed(
  () => !!track.value || (!!songArtist(props.song) && !!songTitle(props.song))
)
const playLabel = computed(() =>
  isCurrent.value && player.isPlaying.value
    ? t('player.pause')
    : t('actions.playItem', { name: songTitle(props.song) })
)
const overlayIcon = computed(() =>
  isCurrent.value && player.isPlaying.value ? 'pause' : 'play'
)

// The whole list as one player queue: downloaded rows from the library,
// the rest left to the player's stream resolution when their turn comes.
function queueTracks() {
  const list = props.songs?.length ? props.songs : [props.song]
  const tracks = list.map((song) => songToPlayerTrack(song, library.findTrack))
  const at = Math.max(
    0,
    list.findIndex((s) => s === props.song || rowKey(s) === rowKey(props.song))
  )
  return { tracks, at }
}

// The play button: the song from the library (with the list queued
// behind it), else its full stream - which the same button pauses.
function toggle() {
  if (track.value && !streaming.value) {
    const { tracks, at } = queueTracks()
    actions.play(tracks, at)
    return
  }
  if (streaming.value) {
    player.toggle()
    return
  }
  const { tracks, at } = queueTracks()
  actions.play(tracks, at)
}

const inLibrary = computed(() =>
  library.hasSong(artistName.value, props.song.name)
)

// Every row already is a downloadable song (video id + link).
const downloadable = computed(() => !!String(props.song.song_id || '').trim())

async function resolveAndDownload() {
  if (resolving.value || resolved.value) return
  resolving.value = true
  try {
    const res = await API.search(`${artistName.value} ${props.song.name}`)
    const first = res.data?.[0]
    if (!first) {
      ui.toast(t('similar.noDownloadMatch', { name: props.song.name }), {
        kind: 'error',
      })
      return
    }
    resolved.value = first
    dm.queue(first)
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('similar.resolveFailed'), {
      kind: 'error',
    })
  } finally {
    resolving.value = false
  }
}
</script>
