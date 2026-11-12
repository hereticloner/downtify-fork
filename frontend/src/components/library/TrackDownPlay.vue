<template>
  <div
    class="group relative flex h-14 items-center gap-3 border-b border-line-2 px-3 transition-colors duration-100 last:border-b-0"
    :class="
      highlighted
        ? 'bg-invert text-on-invert'
        : selected
          ? 'bg-surface-2'
          : 'hover:bg-surface-2'
    "
    :data-marked="marked || undefined"
    @click="onRowClick"
    @dblclick="ensurePlaying"
  >
    <!-- The playing row carries a 4px accent bar on its left edge; a ticked
         one, while nothing is playing on it, the same mark. -->
    <span
      v-if="highlighted || (selectable && selected)"
      class="absolute inset-y-0 left-0 w-1 bg-accent"
      aria-hidden="true"
    />
    <button
      v-if="selectable"
      type="button"
      role="checkbox"
      :aria-checked="selected"
      :aria-label="t('library.selectTrack', { title: song.name })"
      class="flex size-4 shrink-0 items-center justify-center border-2 transition-colors duration-100"
      :class="
        selected
          ? 'border-line bg-invert text-on-invert'
          : highlighted
            ? 'border-on-invert hover:border-accent'
            : 'border-line-3 hover:border-line'
      "
      @click.stop="emit('toggle')"
      @dblclick.stop
    >
      <AppIcon v-if="selected" name="check" :size="11" stroke-width="3" />
    </button>
    <span
      v-if="index !== null"
      class="flex w-6 items-center justify-center max-sm:hidden"
    >
      <EqBars v-if="isCurrent" :size="12" :playing="player.isPlaying.value" />
      <!-- A clip that isn't downloaded yet, while it is loaded: play/pause
           with a frame that fills as the clip goes, where the number was. -->
      <button
        v-else-if="previewActive"
        type="button"
        class="relative grid size-6 place-items-center"
        :aria-label="playLabel"
        @click.stop="toggle"
      >
        <svg
          class="absolute inset-0 size-full -rotate-90"
          viewBox="0 0 24 24"
          fill="none"
          stroke-width="2"
          aria-hidden="true"
        >
          <circle
            cx="12"
            cy="12"
            :r="PREVIEW_RING_RADIUS"
            stroke="currentColor"
            stroke-opacity="0.25"
          />
          <circle
            cx="12"
            cy="12"
            :r="PREVIEW_RING_RADIUS"
            class="stroke-accent"
            stroke-linecap="butt"
            :stroke-dasharray="PREVIEW_RING_LENGTH"
            :stroke-dashoffset="ringOffset(progress)"
            style="transition: stroke-dashoffset 250ms linear"
          />
        </svg>
        <AppIcon
          :name="previewPlaying ? 'pause' : 'play'"
          :size="10"
          :class="previewLoading ? 'animate-pulse' : ''"
        />
      </button>
      <template v-else>
        <span
          class="mono tabular"
          :class="[
            playable ? 'group-hover:hidden' : '',
            highlighted ? 'text-on-invert' : 'text-faint',
          ]"
          >{{ index + 1 }}</span
        >
        <button
          v-if="playable"
          type="button"
          class="hidden group-hover:block"
          :class="highlighted ? 'text-on-invert' : 'text-fg'"
          :aria-label="playLabel"
          @click.stop="toggle"
        >
          <AppIcon name="play" :size="14" />
        </button>
      </template>
    </span>

    <button
      v-if="playable"
      type="button"
      class="shrink-0"
      :aria-label="playLabel"
      @click.stop="toggle"
    >
      <CoverArt
        :src="cover"
        :name="song.album_name || song.name"
        :letter-size="14"
        class="size-10"
      />
    </button>
    <CoverArt
      v-else
      :src="cover"
      :name="song.album_name || song.name"
      :letter-size="14"
      class="size-10"
    />

    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <RouterLink
          v-if="to"
          :to="to"
          class="truncate text-sm font-semibold hover:underline"
          @click.stop
          @dblclick.stop
          >{{ song.name }}</RouterLink
        >
        <span v-else class="truncate text-sm font-semibold">{{
          song.name
        }}</span>
        <span
          v-if="song.explicit"
          class="flex size-4 shrink-0 items-center justify-center border text-[9px] leading-none font-bold"
          :class="highlighted ? 'border-on-invert' : 'border-line-2 text-muted'"
          :title="t('search.explicit')"
          >E</span
        >
      </p>
      <p
        class="truncate text-[13px]"
        :class="highlighted ? 'text-on-invert' : 'text-muted'"
      >
        {{ artists
        }}<span v-if="song.album_name && !hideAlbum" class="lg:hidden">
          · {{ song.album_name }}</span
        >
      </p>
    </div>
    <span
      v-if="!hideAlbum"
      class="hidden w-[26%] truncate text-[13px] lg:block"
      :class="highlighted ? 'text-on-invert' : 'text-muted'"
      >{{ song.album_name }}</span
    >
    <span
      class="mono relative hidden w-12 text-right sm:block"
      :class="highlighted ? 'text-on-invert' : 'text-muted'"
    >
      <!-- Only a clip to hear (not downloaded): its length gives way to
           "Preview" while the row is hovered, and for as long as the clip is
           loaded (the row stays highlighted then, like a hovered one, with
           the mouse gone). The length is hidden, not removed, so nothing
           moves; the label sits on the cell's right edge and may run a little
           to its left, over the gap before it. -->
      <span
        :class="
          previewable
            ? previewActive
              ? 'invisible'
              : 'group-hover:invisible'
            : ''
        "
        >{{ song.duration ? formatDuration(song.duration) : '' }}</span
      >
      <span
        v-if="previewable"
        class="eyebrow pointer-events-none absolute inset-y-0 right-0 items-center whitespace-nowrap"
        :class="previewActive ? 'flex' : 'hidden group-hover:flex'"
        >{{ t('actions.previewLabel') }}</span
      >
    </span>
    <!-- Not downloaded: the download button, with its progress and retry;
         downloaded: the "In library" label. Playing is on the left. A click
         here is the download's own, never the row's (a tap plays). -->
    <div class="flex w-28 shrink-0 justify-end" @click.stop @dblclick.stop>
      <DownloadState :song="song" />
    </div>
  </div>
</template>

<script setup>
// One song as a row that downloads, then plays: a ruled line in a table of
// results, with the play affordances TrackList has on an album page once the
// song is in the library (the number turns into a play button on hover, the
// cover plays, a double click plays, a tap plays on a touch screen). On the
// right it shows the download state - the button, its progress, or the "In
// library" label - the way a search result does.
//
// Until the song is downloaded the same affordances play its 30 s preview
// clip: on the row itself, without the built-in player - see
// model/songPlay.js and model/preview.js.
//
// Deliberately standalone: it borrows the structure of SongRow and the
// behaviour of TrackList without importing or editing either, so neither
// grid can be affected by it. It takes a *song* (what a search or link
// result is), not a library track, and finds the file behind it once it has
// been downloaded.
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import DownloadState from '../search/DownloadState.vue'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import { deezerImage } from '/src/lib/deezerImage'
import { formatDuration } from '/src/lib/format'
import {
  PREVIEW_RING_LENGTH,
  PREVIEW_RING_RADIUS,
  ringOffset,
} from '/src/lib/preview'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // A song from a search/link/top-songs result.
  song: { type: Object, required: true },
  // Its position in the list, shown as the number; `null` hides it.
  index: { type: Number, default: null },
  // The library tracks playing this song starts a queue from (typically the
  // list's other downloaded songs, in order). Without it, just this song.
  queue: { type: Array, default: () => [] },
  // Where the queue comes from, for the player's "playing from".
  context: { type: Object, default: null },
  // Off by default: a caller doing multi-select (e.g. a "download selected"
  // list) turns this on and owns the actual selection state itself - this
  // row only shows the checkbox and reports clicks on it via `toggle`.
  selectable: { type: Boolean, default: false },
  // Whether this row is currently selected. Ignored unless `selectable`.
  selected: { type: Boolean, default: false },
  // Makes the title a link to this route location (e.g. a page about the
  // song); a plain title when unset.
  to: { type: [String, Object], default: null },
  // Highlights the row like the one playing - for a caller pointing at
  // one song in the list (the Finder's, for the track it was opened on).
  marked: { type: Boolean, default: false },
  // Leaves out the album column (and the album after the artists on a
  // narrow screen) - for a list that is all one album anyway.
  hideAlbum: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle'])

const { t } = useI18n()
const player = usePlayer()
const {
  isCurrent,
  previewable,
  previewActive,
  previewPlaying,
  previewLoading,
  playable,
  highlighted: playing,
  playLabel,
  progress,
  toggle,
  ensurePlaying,
} = useSongPlay(props)

const artists = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)
// A Deezer cover at its medium size, for the 40px thumbnail - display only:
// the song's own `cover_url` is what its download embeds.
const cover = computed(() => deezerImage(props.song.cover_url))
// Lit up while it plays (or its clip does), and when the caller points at it.
// Inverted, like every playing row: the plate turns to ink.
const highlighted = computed(() => props.marked || playing.value)

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick() {
  if (window.matchMedia('(pointer: coarse)').matches) toggle()
}
</script>
