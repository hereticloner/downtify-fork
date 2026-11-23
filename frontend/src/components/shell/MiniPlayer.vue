<template>
  <Transition name="now-playing">
    <div
      v-if="track && !nowPlaying.isOpen.value"
      class="fixed inset-x-0 bottom-0 z-40 flex flex-col border-t-2 border-line bg-invert text-on-invert"
      role="region"
      :aria-label="t('player.nowPlaying')"
    >
      <!-- Phones: 56px — cover, title, three transport buttons, then the
           thin segmented line along the bottom edge. -->
      <div class="flex h-11 items-center gap-2 px-2 md:hidden">
        <button
          type="button"
          class="flex min-w-0 flex-1 items-center gap-2 text-left"
          :aria-label="t('player.openNowPlaying')"
          @click="nowPlaying.open()"
        >
          <CoverArt
            :src="track.hasCover ? track.cover : ''"
            :name="track.album || track.title"
            :letter-size="12"
            :icon-size="14"
            class="size-10"
          />
          <span class="min-w-0 flex-1">
            <span class="flex items-center gap-1.5">
              <span class="truncate text-[13px] leading-tight font-medium">{{
                track.title
              }}</span>
              <EqBars v-if="player.isPlaying.value" :size="8" />
            </span>
            <span
              class="block truncate text-[11px] leading-tight text-on-invert/70"
              >{{ trackArtist }}</span
            >
          </span>
        </button>
        <button
          type="button"
          class="flex size-8 shrink-0 items-center justify-center border-2 border-on-invert/40 text-on-invert transition-colors duration-100 hover:border-on-invert hover:bg-on-invert/10"
          :aria-label="t('player.previous')"
          @click="player.prev()"
        >
          <AppIcon name="prev" :size="16" />
        </button>
        <button
          type="button"
          class="play-glow flex size-9 shrink-0 items-center justify-center border-2 border-on-invert bg-on-invert text-invert transition-colors duration-100 hover:bg-on-invert/80"
          :aria-label="
            player.isPlaying.value ? t('player.pause') : t('player.play')
          "
          @click="player.toggle()"
        >
          <Transition name="fade" mode="out-in">
            <span
              v-if="player.isBuffering.value && player.isPlaying.value"
              key="buffer"
              class="size-2.5 animate-pulse bg-current"
              aria-hidden="true"
            />
            <AppIcon
              v-else
              :key="player.isPlaying.value ? 'pause' : 'play'"
              :name="player.isPlaying.value ? 'pause' : 'play'"
              :size="16"
            />
          </Transition>
        </button>
        <button
          type="button"
          class="flex size-8 shrink-0 items-center justify-center border-2 border-on-invert/40 text-on-invert transition-colors duration-100 hover:border-on-invert hover:bg-on-invert/10"
          :aria-label="t('player.next')"
          @click="player.next()"
        >
          <AppIcon name="next" :size="16" />
        </button>
      </div>
      <WaveSeekBar
        class="md:hidden"
        :model-value="scrub ?? player.currentTime.value"
        :max="player.duration.value || 1"
        :label="t('player.seek')"
        :value-text="formatDuration(player.currentTime.value)"
        :playing="player.isPlaying.value"
        @update:model-value="(v) => (scrub = v)"
        @commit="commitSeek"
      />

      <!-- Desktop: 64px transport bar, cover + meta, centred controls over
           the segmented meter, volume and queue on the right. -->
      <div class="hidden h-16 items-center gap-4 px-4 md:flex lg:px-6">
        <div class="flex w-[204px] shrink-0 items-center gap-1.5 lg:w-[264px]">
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-2.5 text-left"
            :aria-label="t('player.openNowPlaying')"
            @click="nowPlaying.open()"
          >
            <CoverArt
              :src="track.hasCover ? track.cover : ''"
              :name="track.album || track.title"
              :letter-size="12"
              :icon-size="14"
              class="size-10"
            />
            <span class="flex min-w-0 flex-col">
              <span class="flex items-center gap-1.5">
                <span class="truncate text-sm leading-tight font-medium">{{
                  track.title
                }}</span>
                <EqBars v-if="player.isPlaying.value" :size="9" />
              </span>
              <span
                class="truncate text-[11px] leading-tight text-on-invert/70"
                >{{ trackArtist }}</span
              >
            </span>
          </button>
          <!-- The heart sits beside the button that opens Now playing, so
               tapping it never opens the overlay. -->
          <span
            v-if="!track?.stream"
            class="hidden shrink-0 lg:flex [&_button]:border-on-invert/40 [&_button]:text-on-invert"
            ><LikeButton :file="track.file"
          /></span>
        </div>

        <div class="flex min-w-0 flex-1 flex-col justify-center">
          <div class="flex items-center justify-center gap-1">
            <button
              v-if="canSimilar"
              type="button"
              class="hidden size-8 items-center justify-center border-2 border-transparent text-on-invert/80 transition-colors duration-100 hover:border-on-invert/40 hover:bg-on-invert/10 hover:text-on-invert lg:flex"
              :aria-label="t('similar.findSimilar')"
              @click="goSimilar"
            >
              <AppIcon name="wand" :size="16" />
            </button>
            <button
              type="button"
              class="flex size-8 items-center justify-center border-2 transition-colors duration-100"
              :class="
                player.shuffle.value
                  ? 'border-on-invert bg-on-invert text-invert'
                  : 'border-transparent text-on-invert/80 hover:border-on-invert/40 hover:bg-on-invert/10 hover:text-on-invert'
              "
              :aria-label="t('player.shuffle')"
              :aria-pressed="player.shuffle.value"
              @click="player.toggleShuffle()"
            >
              <AppIcon name="shuffle" :size="16" />
            </button>
            <button
              type="button"
              class="flex size-9 items-center justify-center border-2 border-transparent text-on-invert transition-colors duration-100 hover:border-on-invert/40 hover:bg-on-invert/10"
              :aria-label="t('player.previous')"
              @click="player.prev()"
            >
              <AppIcon name="prev" :size="18" />
            </button>
            <button
              type="button"
              class="play-glow flex size-10 items-center justify-center border-2 border-on-invert bg-on-invert text-invert transition-colors duration-100 hover:bg-on-invert/80"
              :aria-label="
                player.isPlaying.value ? t('player.pause') : t('player.play')
              "
              @click="player.toggle()"
            >
              <Transition name="fade" mode="out-in">
                <span
                  v-if="player.isBuffering.value && player.isPlaying.value"
                  key="buffer"
                  class="size-3 animate-pulse bg-current"
                  aria-hidden="true"
                />
                <AppIcon
                  v-else
                  :key="player.isPlaying.value ? 'pause' : 'play'"
                  :name="player.isPlaying.value ? 'pause' : 'play'"
                  :size="18"
                />
              </Transition>
            </button>
            <button
              type="button"
              class="flex size-9 items-center justify-center border-2 border-transparent text-on-invert transition-colors duration-100 hover:border-on-invert/40 hover:bg-on-invert/10"
              :aria-label="t('player.next')"
              @click="player.next()"
            >
              <AppIcon name="next" :size="18" />
            </button>
            <button
              type="button"
              class="flex size-8 items-center justify-center border-2 transition-colors duration-100"
              :class="
                player.repeatMode.value !== 'off'
                  ? 'border-on-invert bg-on-invert text-invert'
                  : 'border-transparent text-on-invert/80 hover:border-on-invert/40 hover:bg-on-invert/10 hover:text-on-invert'
              "
              :aria-label="repeatLabel"
              :aria-pressed="player.repeatMode.value !== 'off'"
              @click="player.cycleRepeat()"
            >
              <AppIcon
                :name="
                  player.repeatMode.value === 'one' ? 'repeat-one' : 'repeat'
                "
                :size="16"
              />
            </button>
            <button
              v-if="showMiniDownload"
              type="button"
              class="hidden size-8 items-center justify-center border-2 border-transparent text-on-invert/80 transition-colors duration-100 hover:border-on-invert/40 hover:bg-on-invert/10 hover:text-on-invert disabled:opacity-40 lg:flex"
              :aria-label="t('actions.downloadItem', { name: trackTitle })"
              :disabled="downloadBusy"
              @click="downloadCurrent"
            >
              <AppIcon
                :name="downloadBusy ? 'refresh' : 'download'"
                :size="16"
                :class="downloadBusy ? 'animate-spin' : ''"
              />
            </button>
            <!-- Downloaded tracks show a static check in the download
                 button's slot: it does nothing, deleting happens from the
                 library rows. -->
            <span
              v-if="showDownloadedCheck"
              class="hidden size-8 items-center justify-center text-accent lg:flex"
              :title="t('search.inLibrary')"
              aria-hidden="true"
            >
              <AppIcon name="check" :size="16" />
            </span>
          </div>

          <div class="mt-0.5 flex items-center gap-3">
            <span
              class="mono tabular w-10 shrink-0 text-right text-on-invert/70"
              >{{ formatDuration(scrub ?? player.currentTime.value) }}</span
            >
            <WaveSeekBar
              class="flex-1"
              :model-value="scrub ?? player.currentTime.value"
              :max="player.duration.value || 1"
              :label="t('player.seek')"
              :value-text="formatDuration(player.currentTime.value)"
              :playing="player.isPlaying.value"
              @update:model-value="(v) => (scrub = v)"
              @commit="commitSeek"
            />
            <span class="mono tabular w-10 shrink-0 text-on-invert/70">{{
              formatDuration(player.duration.value)
            }}</span>
          </div>
        </div>

        <div
          class="flex w-[204px] shrink-0 items-center justify-end gap-1 lg:w-[264px]"
        >
          <div
            class="hidden items-center gap-1 [&_button:hover]:bg-on-invert/10 [&_button]:border-on-invert/40 [&_button]:text-on-invert lg:flex"
          >
            <VolumeControl
              width="w-20 min-w-8"
              track-class="bg-on-invert/25"
              fill-class="bg-on-invert"
              thumb-class="bg-on-invert"
            />
          </div>
          <button
            v-if="showLyrics"
            type="button"
            class="hidden size-8 items-center justify-center border-2 border-on-invert/40 text-on-invert transition-colors duration-100 hover:border-on-invert hover:bg-on-invert/10 lg:flex"
            :aria-label="t('player.lyrics')"
            @click="nowPlaying.open('lyrics')"
          >
            <AppIcon name="lyrics" :size="16" />
          </button>
          <button
            type="button"
            class="flex size-8 items-center justify-center border-2 border-on-invert/40 text-on-invert transition-colors duration-100 hover:border-on-invert hover:bg-on-invert/10"
            :aria-label="t('player.upNext')"
            @click="nowPlaying.open('queue')"
          >
            <AppIcon name="queue" :size="16" />
          </button>
          <button
            type="button"
            class="flex size-8 items-center justify-center border-2 border-on-invert/40 text-on-invert transition-colors duration-100 hover:border-on-invert hover:bg-on-invert/10"
            :aria-label="t('player.openNowPlaying')"
            @click="nowPlaying.open()"
          >
            <AppIcon name="expand" :size="16" />
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import LikeButton from '../player/LikeButton.vue'
import WaveSeekBar from '../player/WaveSeekBar.vue'
import VolumeControl from '../player/VolumeControl.vue'
import { usePlayer } from '/src/model/player'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useNowPlaying, useUi } from '/src/model/ui'
import { formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { showLyrics } = usePlayerPrefs()
const nowPlaying = useNowPlaying()
const { t } = useI18n()
const router = useRouter()
const library = useLibrary()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const ui = useUi()
const scrub = ref(null)

const track = computed(() => player.currentTrack.value)

const trackArtist = computed(
  () =>
    (track.value?.artists || [])[0] ||
    track.value?.artist ||
    t('common.unknownArtist')
)
const trackTitle = computed(() => track.value?.name || track.value?.title || '')

const canSimilar = computed(() => {
  if (track.value?.isPodcast) return false
  const artist = (track.value?.artists || [])[0] || track.value?.artist || ''
  const title = track.value?.name || track.value?.title || ''
  return !!artist.trim() && !!title.trim()
})

function goSimilar() {
  const artist = (track.value?.artists || [])[0] || track.value?.artist || ''
  const title = track.value?.name || track.value?.title || ''
  if (!artist.trim() || !title.trim()) return
  router.push({ name: 'Similar', query: { artist, track: title } })
}

// A stream that isn't in the library yet can be queued from here; while
// queued it spins instead of queueing a duplicate.
const streamDownloadable = computed(
  () =>
    !!track.value?.stream &&
    !!track.value.video_id &&
    !library.hasSong(trackArtist.value, trackTitle.value)
)
const pendingSong = computed(() => {
  if (!streamDownloadable.value) return null
  const tr = track.value
  return {
    name: trackTitle.value,
    artists: tr.artist ? [tr.artist] : [],
    artist: tr.artist || '',
    album_name: tr.album || '',
    cover_url: tr.cover && String(tr.cover).startsWith('http') ? tr.cover : '',
    duration: tr.duration || 0,
    url: `https://music.youtube.com/watch?v=${tr.video_id}`,
    youtube_id: tr.video_id,
  }
})
const downloadJob = computed(() => {
  tracker.queueVersion.value
  return pendingSong.value ? tracker.getBySong(pendingSong.value) : null
})
const downloadBusy = computed(() => {
  const state = downloadJob.value?.state
  return state === 'queued' || state === 'active'
})
const showMiniDownload = computed(() => !!streamDownloadable.value)

function downloadCurrent() {
  const song = pendingSong.value
  if (!song || downloadBusy.value) return
  if (downloadJob.value?.state === 'failed') dm.retry(song)
  else {
    dm.queue(song)
    ui.toast(t('toast.queuedTracks', { count: 1, name: song.name }), {
      kind: 'success',
    })
  }
}

// A downloaded track (or a stream that landed in the library while
// playing) shows a static check where the download button was.
const showDownloadedCheck = computed(
  () =>
    !!track.value &&
    !track.value.isPodcast &&
    (!track.value.stream ||
      library.hasSong(trackArtist.value, trackTitle.value))
)

const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}
</script>
