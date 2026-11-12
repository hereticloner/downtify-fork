<template>
  <Teleport to="body">
    <Transition name="now-playing">
      <div
        v-if="nowPlaying.isOpen.value && track"
        class="fixed inset-0 z-50 flex flex-col overflow-hidden bg-bg text-fg"
        role="dialog"
        aria-modal="true"
        :aria-label="t('player.nowPlaying')"
      >
        <!-- Header: 44px inverted band, close on the left, what is playing
             in the middle, the track menu on the right. -->
        <header
          class="flex h-11 shrink-0 items-stretch border-b-2 border-line bg-invert text-on-invert"
        >
          <button
            ref="closeButton"
            type="button"
            class="flex w-11 shrink-0 items-center justify-center border-r-2 border-on-invert/25 transition-colors duration-100 hover:bg-on-invert/10"
            :aria-label="t('player.closeNowPlaying')"
            @click="nowPlaying.close()"
          >
            <AppIcon name="chevron-down" :size="18" />
          </button>
          <component
            :is="contextRoute ? RouterLink : 'div'"
            :to="contextRoute || undefined"
            class="flex min-w-0 flex-1 items-center justify-center gap-2 px-3"
          >
            <CoverArt
              v-if="
                context?.type === 'playlist' &&
                (context.cover || context.covers?.length)
              "
              :src="context.cover || ''"
              :covers="context.covers || []"
              :name="context.title"
              :letter-size="8"
              :icon-size="10"
              class="size-6 shrink-0"
            />
            <span class="flex min-w-0 flex-col">
              <span class="eyebrow text-on-invert/60">{{ contextLabel }}</span>
              <span class="truncate text-[12px] leading-tight font-medium">{{
                contextTitle
              }}</span>
            </span>
          </component>
          <UiMenu :items="trackMenu" :label="t('common.more')">
            <template #trigger>
              <button
                type="button"
                class="flex h-11 w-11 items-center justify-center border-l-2 border-on-invert/25 transition-colors duration-100 hover:bg-on-invert/10"
                :aria-label="t('common.more')"
              >
                <AppIcon name="more" :size="18" />
              </button>
            </template>
          </UiMenu>
        </header>

        <!-- Body: square artwork and its plate on the left, the panel block
             on the right; phones show one or the other. -->
        <div
          class="flex min-h-0 flex-1 justify-center overflow-hidden px-4 lg:px-8"
        >
          <div
            class="flex min-h-0 w-full max-w-[1200px] flex-col gap-5 py-4 lg:flex-row lg:gap-8 lg:py-6"
          >
            <div
              class="flex min-h-0 flex-col gap-4 overflow-y-auto lg:w-[380px] lg:shrink-0 lg:justify-center"
              :class="mobilePanel ? 'max-lg:hidden' : ''"
            >
              <CoverArt
                :src="track.hasCover ? track.cover : ''"
                :name="track.album || track.title"
                :letter-size="120"
                :icon-size="64"
                class="mx-auto aspect-square w-full max-w-[22rem] lg:max-w-none"
              />
              <div class="flex items-end justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <h2
                    class="text-display truncate text-3xl font-bold lg:text-4xl"
                  >
                    {{ track.title }}
                  </h2>
                  <RouterLink
                    v-if="artistName"
                    :to="{ name: 'Artist', query: { name: artistName } }"
                    class="mt-1 block truncate text-sm text-muted hover:text-fg hover:underline"
                    >{{ track.artist }}</RouterLink
                  >
                  <p v-else class="mt-1 truncate text-sm text-muted">
                    {{ track.artist }}
                  </p>
                </div>
                <div class="flex shrink-0 items-center gap-1">
                  <LikeButton
                    v-if="!track?.stream"
                    :file="track.file"
                    size="lg"
                  />
                </div>
              </div>
              <p
                v-if="techLine"
                class="mono flex flex-wrap items-center gap-x-2 gap-y-1 text-faint"
              >
                {{ techLine }}
              </p>
              <p
                v-if="player.playError.value"
                class="flex items-center gap-2 text-sm text-danger"
              >
                <AppIcon name="alert" :size="16" />{{ t('player.cannotPlay') }}
              </p>
            </div>

            <!-- Panel: three block tabs over the existing panel components. -->
            <div
              class="flex min-h-0 flex-1 flex-col border-2 border-line"
              :class="mobilePanel ? '' : 'max-lg:hidden'"
            >
              <div
                role="tablist"
                class="flex shrink-0 items-stretch border-b-2 border-line"
              >
                <button
                  v-for="tab in panels"
                  :key="tab.id"
                  type="button"
                  role="tab"
                  :aria-selected="panelActive(tab.id)"
                  class="flex h-11 min-w-0 flex-1 items-center justify-center gap-2 border-l-2 border-line px-2 transition-colors duration-100 first:border-l-0"
                  :class="
                    panelActive(tab.id)
                      ? 'bg-invert text-on-invert'
                      : 'text-muted hover:bg-surface-2 hover:text-fg'
                  "
                  @click="onTab(tab.id)"
                >
                  <AppIcon :name="tab.icon" :size="15" />
                  <span
                    class="eyebrow truncate"
                    :class="panelActive(tab.id) ? 'text-on-invert' : ''"
                    >{{ tab.label }}</span
                  >
                </button>
              </div>
              <div class="flex min-h-0 flex-1 flex-col p-2 lg:p-3">
                <LyricsPanel v-if="panel === 'lyrics'" :compact="isMobile" />
                <UpNextPanel v-else-if="panel === 'queue'" />
                <TrackDetails v-else-if="panel === 'details'" />
                <EqualizerPanel v-else-if="panel === 'equalizer'" />
              </div>
            </div>
          </div>
        </div>

        <!-- Transport: segmented meter and the squared controls. -->
        <footer class="shrink-0 border-t-2 border-line">
          <div
            class="mx-auto flex max-w-[1200px] flex-col gap-1.5 px-4 py-2 lg:px-8"
          >
            <div class="flex items-center gap-3">
              <span class="mono tabular w-10 shrink-0 text-right text-muted">{{
                formatDuration(scrub ?? player.currentTime.value)
              }}</span>
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
              <span class="mono tabular w-10 shrink-0 text-muted">{{
                formatDuration(player.duration.value)
              }}</span>
            </div>

            <div class="flex items-center gap-2">
              <div class="hidden flex-1 items-center gap-2 lg:flex">
                <UiBadge v-if="track.format">{{ track.format }}</UiBadge>
                <span v-if="track.size" class="mono text-faint">{{
                  formatBytes(track.size)
                }}</span>
              </div>

              <div
                class="flex flex-1 items-center justify-center gap-1 lg:flex-none lg:gap-2"
              >
                <!-- Tracks like this one (podcasts and anonymous streams
                     have none). -->
                <button
                  v-if="similarArtist && similarTitle"
                  type="button"
                  class="flex size-9 items-center justify-center border-2 border-line-2 text-muted transition-colors duration-100 hover:border-line hover:bg-surface-2 hover:text-fg"
                  :aria-label="t('similar.findSimilar')"
                  @click="goSimilar"
                >
                  <AppIcon name="wand" :size="17" />
                </button>
                <button
                  type="button"
                  class="flex size-9 items-center justify-center border-2 transition-colors duration-100"
                  :class="
                    player.shuffle.value
                      ? 'border-line bg-invert text-on-invert'
                      : 'border-line-2 text-muted hover:border-line hover:bg-surface-2 hover:text-fg'
                  "
                  :aria-label="t('player.shuffle')"
                  :aria-pressed="player.shuffle.value"
                  @click="player.toggleShuffle()"
                >
                  <AppIcon name="shuffle" :size="17" />
                </button>
                <button
                  type="button"
                  class="flex size-11 items-center justify-center border-2 border-line-2 text-muted transition-colors duration-100 hover:border-line hover:bg-surface-2 hover:text-fg"
                  :aria-label="t('player.previous')"
                  @click="player.prev()"
                >
                  <AppIcon name="prev" :size="22" />
                </button>
                <button
                  type="button"
                  class="flex size-12 items-center justify-center border-2 border-line bg-invert text-on-invert transition-colors duration-100 hover:bg-fg-3 active:bg-surface active:text-fg"
                  :aria-label="
                    player.isPlaying.value
                      ? t('player.pause')
                      : t('player.play')
                  "
                  @click="player.toggle()"
                >
                  <span
                    v-if="player.isBuffering.value && player.isPlaying.value"
                    class="size-3.5 animate-pulse bg-current"
                    aria-hidden="true"
                  />
                  <AppIcon
                    v-else
                    :name="player.isPlaying.value ? 'pause' : 'play'"
                    :size="22"
                  />
                </button>
                <button
                  type="button"
                  class="flex size-11 items-center justify-center border-2 border-line-2 text-muted transition-colors duration-100 hover:border-line hover:bg-surface-2 hover:text-fg"
                  :aria-label="t('player.next')"
                  @click="player.next()"
                >
                  <AppIcon name="next" :size="22" />
                </button>
                <button
                  type="button"
                  class="flex size-9 items-center justify-center border-2 transition-colors duration-100"
                  :class="
                    player.repeatMode.value !== 'off'
                      ? 'border-line bg-invert text-on-invert'
                      : 'border-line-2 text-muted hover:border-line hover:bg-surface-2 hover:text-fg'
                  "
                  :aria-label="repeatLabel"
                  :aria-pressed="player.repeatMode.value !== 'off'"
                  @click="player.cycleRepeat()"
                >
                  <AppIcon
                    :name="
                      player.repeatMode.value === 'one'
                        ? 'repeat-one'
                        : 'repeat'
                    "
                    :size="17"
                  />
                </button>
                <!-- A stream queues its download (once - while queued it
                     pulses instead), a downloaded track shows a static
                     check that does nothing. -->
                <button
                  v-if="showPlayerDownload"
                  type="button"
                  class="flex size-9 items-center justify-center border-2 border-line-2 text-muted transition-colors duration-100 hover:border-line hover:bg-surface-2 hover:text-fg disabled:opacity-40"
                  :aria-label="t('actions.downloadItem', { name: track.title })"
                  :disabled="downloadBusy"
                  @click="downloadCurrent"
                >
                  <AppIcon
                    :name="downloadBusy ? 'refresh' : 'download'"
                    :size="17"
                    :class="downloadBusy ? 'animate-spin' : ''"
                  />
                </button>
                <span
                  v-else-if="showDownloadedCheck"
                  class="flex size-9 items-center justify-center text-accent"
                  :title="t('search.inLibrary')"
                  aria-hidden="true"
                >
                  <AppIcon name="check" :size="17" />
                </span>
              </div>

              <div class="hidden flex-1 items-center justify-end gap-2 lg:flex">
                <UiMenu
                  :items="sleepMenu"
                  :label="t('player.sleepTimer')"
                  align="start"
                >
                  <template #trigger>
                    <button
                      type="button"
                      class="flex h-9 items-center gap-1.5 border-2 px-2 transition-colors duration-100"
                      :class="
                        player.sleepAt.value
                          ? 'border-accent text-accent'
                          : 'border-line-2 text-muted hover:border-line hover:text-fg'
                      "
                      :aria-label="t('player.sleepTimer')"
                    >
                      <AppIcon name="timer" :size="17" />
                      <span v-if="sleepLabel" class="mono tabular">{{
                        sleepLabel
                      }}</span>
                    </button>
                  </template>
                </UiMenu>
                <VolumeControl width="w-28" />
              </div>
            </div>

            <!-- Phone extras: sleep timer and volume under the transport. -->
            <div class="flex items-center justify-between gap-3 lg:hidden">
              <UiMenu
                :items="sleepMenu"
                :label="t('player.sleepTimer')"
                align="start"
              >
                <template #trigger>
                  <button
                    type="button"
                    class="flex h-8 items-center gap-1.5 border-2 px-2 transition-colors duration-100"
                    :class="
                      player.sleepAt.value
                        ? 'border-accent text-accent'
                        : 'border-line-2 text-muted hover:border-line hover:text-fg'
                    "
                    :aria-label="t('player.sleepTimer')"
                  >
                    <AppIcon name="timer" :size="15" />
                    <span v-if="sleepLabel" class="mono tabular">{{
                      sleepLabel
                    }}</span>
                  </button>
                </template>
              </UiMenu>
              <VolumeControl width="w-28" />
            </div>
          </div>
        </footer>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useMediaQuery, useNow } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiMenu from '../ui/UiMenu.vue'
import WaveSeekBar from '../player/WaveSeekBar.vue'
import VolumeControl from '../player/VolumeControl.vue'
import LikeButton from '../player/LikeButton.vue'
import LyricsPanel from '../player/LyricsPanel.vue'
import UpNextPanel from '../player/UpNextPanel.vue'
import TrackDetails from '../player/TrackDetails.vue'
import EqualizerPanel from '../player/EqualizerPanel.vue'
import { usePlayer } from '/src/model/player'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useNowPlaying } from '/src/model/ui'
import { formatBytes, formatDuration } from '/src/lib/format'
import { availablePanels, defaultPanel, requestedPanel } from '/src/lib/panels'
import { saveName } from '/src/lib/paths'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const library = useLibrary()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const ui = useUi()
const { showLyrics } = usePlayerPrefs()
const nowPlaying = useNowPlaying()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isMobile = useMediaQuery('(max-width: 1023px)')
const now = useNow({ interval: 15000 })
const scrub = ref(null)
const closeButton = ref(null)

const track = computed(() => player.currentTrack.value)

// Tracks like this one (podcasts have none): left of shuffle.
const similarArtist = computed(() => {
  if (track.value?.isPodcast) return ''
  return (track.value?.artists || [])[0] || track.value?.artist || ''
})
const similarTitle = computed(
  () => track.value?.name || track.value?.title || ''
)

function goSimilar() {
  const artist = (
    (track.value?.artists || [])[0] ||
    track.value?.artist ||
    ''
  ).trim()
  const title = (track.value?.name || track.value?.title || '').trim()
  if (!artist || !title) return
  router.push({ name: 'Similar', query: { artist, track: title } })
}

// Technical values, in mono: what the file is, not how it feels.
const techLine = computed(() => {
  const tr = track.value
  if (!tr) return ''
  return [
    tr.format,
    tr.size ? formatBytes(tr.size) : '',
    tr.duration ? formatDuration(tr.duration) : '',
    tr.year,
  ]
    .filter(Boolean)
    .join(' · ')
})

const PANEL_TABS = {
  lyrics: { icon: 'lyrics', label: 'player.lyrics' },
  queue: { icon: 'queue', label: 'player.upNext' },
  details: { icon: 'info', label: 'player.details' },
  equalizer: { icon: 'equalizer', label: 'player.equalizer' },
}

const panels = computed(() =>
  availablePanels({
    lyrics: showLyrics.value,
    isStream: track.value?.stream,
  }).map((id) => ({
    id,
    icon: PANEL_TABS[id].icon,
    label: t(PANEL_TABS[id].label),
  }))
)

// ?panel= picks the side panel; phones show it instead of the artwork.
const requested = computed(() =>
  requestedPanel(
    route.query.panel,
    panels.value.map((tab) => tab.id)
  )
)
const panel = computed(
  () =>
    requested.value ||
    defaultPanel({
      lyrics: showLyrics.value,
      isStream: track.value?.stream,
    })
)
const mobilePanel = computed(() => isMobile.value && !!requested.value)

// On phones the panel replaces the artwork, so the tab for the open panel
// is the only one that reads as selected (tapping it again goes back).
function panelActive(id) {
  return panel.value === id && (!isMobile.value || mobilePanel.value)
}

function setPanel(id) {
  router.replace({ query: { ...route.query, panel: id } })
}

function toggleMobilePanel(id) {
  if (mobilePanel.value && panel.value === id) {
    const { panel: _panel, ...query } = route.query
    router.replace({ query })
  } else {
    setPanel(id)
  }
}

function onTab(id) {
  if (isMobile.value) toggleMobilePanel(id)
  else setPanel(id)
}

const context = computed(() => player.context.value)
const contextLabel = computed(() => {
  const type = context.value?.type
  return type ? t(`player.playingFrom.${type}`) : t('player.nowPlaying')
})
const contextTitle = computed(
  () => context.value?.title || track.value?.album || t('player.queue')
)
const contextRoute = computed(() => context.value?.route || null)

const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

const sleepLabel = computed(() => {
  const at = player.sleepAt.value
  if (!at) return ''
  if (at === 'track') return t('player.sleepEndOfTrackShort')
  const minutes = Math.max(1, Math.ceil((at - now.value.getTime()) / 60000))
  return t('player.minutesLeft', { count: minutes })
})

const sleepMenu = computed(() => [
  { heading: t('player.sleepTimer') },
  ...[15, 30, 45, 60, 90].map((minutes) => ({
    label: t('player.sleepMinutes', { count: minutes }),
    action: () => player.setSleepTimer(minutes),
  })),
  {
    label: t('player.sleepEndOfTrack'),
    checked: player.sleepAt.value === 'track',
    action: () => player.setSleepTimer('track'),
  },
  { divider: true, hidden: !player.sleepAt.value },
  {
    label: t('player.sleepOff'),
    icon: 'x',
    hidden: !player.sleepAt.value,
    action: () => player.setSleepTimer(null),
  },
  {
    heading: t('player.autoDj'),
    hidden: !track.value,
  },
  {
    label: t('player.autoDjOn'),
    checked: player.autoDj.value,
    hidden: !track.value,
    action: () => player.setAutoDj(!player.autoDj.value),
  },
])

// The library keys artists by album artist, but a downloaded file may only
// carry the plain artist tag - fall back so the name always opens a page.
const artistName = computed(
  () => track.value?.albumArtist || track.value?.artist || ''
)

const trackMenu = computed(() => {
  const tr = track.value
  if (!tr) return []
  return [
    {
      label: t('player.goToAlbum'),
      icon: 'disc',
      hidden: !tr.album,
      action: () =>
        navigate({
          name: 'Album',
          query: { artist: artistName.value, title: tr.album },
        }),
    },
    {
      label: t('player.goToArtist'),
      icon: 'user',
      hidden: !artistName.value,
      action: () =>
        navigate({ name: 'Artist', query: { name: artistName.value } }),
    },
    {
      label: t('library.saveToDevice'),
      icon: 'download',
      // A stream has no file to save; its download lives in the
      // transport row instead.
      hidden: !!tr.stream,
      action: () => saveFile(tr),
    },
    { divider: true },
    {
      label: t('player.details'),
      icon: 'info',
      action: () =>
        isMobile.value ? toggleMobilePanel('details') : setPanel('details'),
    },
  ]
})

function navigate(to) {
  // Leave the overlay first so the new page isn't opened "under" it.
  router.replace({ query: {} }).then(() => router.push(to))
}

function saveFile(tr) {
  const a = document.createElement('a')
  a.href = tr.url
  a.download = saveName(tr.file)
  document.body.appendChild(a)
  a.click()
  a.remove()
}

// A stream that landed in the library while playing (downloaded from
// anywhere) offers deletion instead of another download.
const streamDownloaded = computed(
  () =>
    !!track.value?.stream &&
    library.hasSong(track.value.artist, track.value.title)
)

const showPlayerDownload = computed(
  () => !!track.value?.stream && !streamDownloaded.value
)
// A downloaded track shows a static check where the download button
// was; deleting happens from the library rows.
const showDownloadedCheck = computed(
  () =>
    !!track.value &&
    !track.value.isPodcast &&
    (!track.value.stream || streamDownloaded.value)
)

// The playing stream as a downloadable song: the watch URL is the
// download key (so it can't be queued twice) and the known video id
// pins the exact version, like a resolved search row.
const pendingSong = computed(() => {
  const tr = track.value
  if (!tr?.stream || !tr.video_id) return null
  return {
    name: tr.title,
    artists: tr.artist ? [tr.artist] : [],
    artist: tr.artist || '',
    album_name: tr.album || '',
    cover_url: tr.cover && String(tr.cover).startsWith('http') ? tr.cover : '',
    duration: tr.duration || 0,
    url: `https://music.youtube.com/watch?v=${tr.video_id}`,
    youtube_id: tr.video_id,
  }
})

// The queued/finished job behind the button, if any - while one exists
// the button pulses instead of queueing a duplicate.
const downloadJob = computed(() => {
  tracker.queueVersion.value
  return pendingSong.value ? tracker.getBySong(pendingSong.value) : null
})
const downloadBusy = computed(() => {
  const state = downloadJob.value?.state
  return state === 'queued' || state === 'active'
})

/** Queue the playing stream as a download (it keeps streaming). */
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

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}

// Nothing to show once the queue empties.
watch(track, (value) => {
  if (!value && nowPlaying.isOpen.value) nowPlaying.close()
})

watch(
  () => nowPlaying.isOpen.value,
  async (open) => {
    document.documentElement.style.overflow = open ? 'hidden' : ''
    if (open) {
      await nextTick()
      closeButton.value?.focus()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  document.documentElement.style.overflow = ''
})
</script>
