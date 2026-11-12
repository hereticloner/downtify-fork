<template>
  <div class="flex flex-col">
    <!-- The resolver: one field for the address, one inverted block to read
         it again. -->
    <section class="flex flex-col border-b-2 border-line">
      <div class="flex items-stretch border-b-2 border-line bg-surface-2">
        <span
          class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
          >01</span
        >
        <span
          class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
        >
          {{ t('home.inputLabel') }}
        </span>
      </div>
      <form
        class="flex flex-col gap-2 p-4 sm:flex-row sm:items-stretch sm:px-6"
        @submit.prevent="submitUrl"
      >
        <span
          class="flex h-12 min-w-0 flex-1 items-center gap-2.5 border-2 border-line bg-bg px-3 transition-colors duration-100 focus-within:border-accent"
        >
          <AppIcon name="link" :size="16" class="shrink-0 text-faint" />
          <label for="link-url" class="sr-only">{{
            t('home.inputLabel')
          }}</label>
          <input
            id="link-url"
            v-model="urlInput"
            type="text"
            autocomplete="off"
            spellcheck="false"
            :placeholder="t('home.inputPlaceholder')"
            class="mono h-full min-w-0 flex-1 bg-transparent text-fg outline-none placeholder:text-faint"
          />
        </span>
        <UiButton
          type="submit"
          variant="primary"
          size="lg"
          class="sm:-ml-0.5"
          :disabled="!urlInput.trim() || urlInput.trim() === url"
        >
          {{ t('home.getIt') }}
        </UiButton>
      </form>
    </section>

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex flex-col gap-4 border-b-2 border-line p-4 sm:flex-row sm:p-6"
      aria-busy="true"
    >
      <UiSkeleton class="size-40 self-center sm:self-auto" />
      <div class="flex flex-1 flex-col gap-3">
        <UiSkeleton class="h-2.5 w-32" />
        <UiSkeleton class="h-10 w-2/3" />
        <p class="mono flex items-center gap-2 text-muted">
          <span class="size-2 animate-pulse bg-accent" aria-hidden="true" />
          {{ t('link.resolving') }}
        </p>
      </div>
    </div>

    <div v-else-if="error" class="border-b-2 border-line p-4" role="status">
      <UiEmpty icon="alert" :title="t('link.failed')" :body="error">
        <UiButton icon="refresh" @click="resolve">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="details" class="animate-rise flex flex-col">
      <CollectionHero
        :title="details.name || t('link.untitled')"
        :kicker="kicker"
        :cover="details.cover_url"
        :covers="details.cover_url ? [] : mosaic"
        :name="details.name"
        :icon="
          details.kind === 'artist'
            ? 'user'
            : details.kind === 'playlist'
              ? 'playlist'
              : 'disc'
        "
        :round="details.kind === 'artist'"
      >
        <template #subtitle>
          <span v-if="details.subtitle" class="line-clamp-2">{{
            details.subtitle
          }}</span>
          <span v-if="details.tracks.length" class="tabular">
            {{
              [
                details.year,
                t('common.tracks', { count: details.tracks.length }),
                lengthLabel,
              ]
                .filter(Boolean)
                .join(' · ')
            }}
          </span>
          <span v-else-if="details.albums.length">
            {{ t('link.releases', { count: details.albums.length }) }}
          </span>
        </template>
        <template #actions>
          <template v-if="details.tracks.length">
            <UiButton
              v-if="newSongs.length"
              variant="primary"
              size="lg"
              icon="download"
              :loading="submitting"
              @click="download(newSongs)"
            >
              {{
                newSongs.length === details.tracks.length
                  ? t('link.downloadAll', { count: newSongs.length })
                  : t('link.downloadNew', { count: newSongs.length })
              }}
            </UiButton>
            <span
              v-else
              class="flex h-12 items-center gap-2 border-2 border-line px-5"
            >
              <AppIcon name="check-circle" :size="16" />
              <span class="eyebrow text-fg">{{ t('link.allInLibrary') }}</span>
            </span>
            <UiButton
              v-if="newSongs.length && newSongs.length < details.tracks.length"
              size="lg"
              @click="download(details.tracks)"
            >
              {{ t('link.redownloadAll') }}
            </UiButton>
          </template>
          <UiButton
            v-if="watchable"
            size="lg"
            icon="radar"
            :loading="watching"
            @click="watch"
          >
            {{
              details.kind === 'artist'
                ? t('link.watchArtist')
                : t('link.watchPlaylist')
            }}
          </UiButton>
          <UiButton
            v-if="details.kind === 'artist'"
            size="lg"
            icon="trending"
            :to="{ name: 'TopSongs', query: { url } }"
          >
            {{ t('link.topSongs') }}
          </UiButton>
          <UiButton variant="plain" size="lg" icon="arrow-up-right" :href="url">
            <span class="max-sm:sr-only">{{ sourceLabel }}</span>
          </UiButton>
        </template>
      </CollectionHero>

      <!-- Tracks -->
      <template v-if="details.tracks.length">
        <div
          class="flex flex-wrap items-center gap-2 border-b-2 border-line px-3 py-2"
        >
          <UiChips v-model="filter" :items="filters" />
          <span v-if="selected.size" class="ml-auto flex items-center gap-2">
            <span class="mono text-muted">{{
              t('library.selectedCount', { count: selected.size })
            }}</span>
            <UiButton
              size="sm"
              variant="primary"
              icon="download"
              @click="download(selectedSongs)"
            >
              {{ t('link.downloadSelected') }}
            </UiButton>
            <UiIconButton
              icon="x"
              :label="t('library.clearSelection')"
              size="sm"
              @click="selected = new Set()"
            />
          </span>
        </div>
        <div class="border-2 border-line">
          <TrackDownPlayHeader selectable />
          <ol class="flex flex-col">
            <li
              v-for="row in visibleRows"
              :key="row.key"
              class="relative flex h-14 items-center gap-3 border-b border-line-2 px-3 transition-colors duration-100 last:border-b-0"
              :class="
                selected.has(row.key) ? 'bg-surface-2' : 'hover:bg-surface-2'
              "
            >
              <span
                v-if="selected.has(row.key)"
                class="absolute inset-y-0 left-0 w-1 bg-accent"
                aria-hidden="true"
              />
              <button
                type="button"
                role="checkbox"
                :aria-checked="selected.has(row.key)"
                :aria-label="t('library.selectTrack', { title: row.song.name })"
                class="flex size-4 shrink-0 items-center justify-center border-2 transition-colors duration-100"
                :class="
                  selected.has(row.key)
                    ? 'border-line bg-invert text-on-invert'
                    : 'border-line-3 hover:border-line'
                "
                @click="toggle(row.key)"
              >
                <AppIcon
                  v-if="selected.has(row.key)"
                  name="check"
                  :size="11"
                  stroke-width="3"
                />
              </button>
              <SongPlayCell
                :song="row.song"
                :index="row.index"
                :queue="playQueue"
                :context="playContext"
              />
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
              <span
                class="hidden w-[26%] truncate text-[13px] text-muted lg:block"
                >{{ row.song.album_name }}</span
              >
              <span
                class="mono tabular hidden w-12 text-right text-muted sm:block"
              >
                {{ row.song.duration ? formatDuration(row.song.duration) : '' }}
              </span>
              <div class="flex w-28 shrink-0 justify-end">
                <DownloadState :song="row.song" />
              </div>
            </li>
          </ol>
        </div>
        <p
          v-if="!visibleRows.length"
          class="border-b-2 border-line px-3 py-8 text-center text-[13px] text-muted"
        >
          {{ t('library.noMatches') }}
        </p>
      </template>

      <!-- Artist releases -->
      <div
        v-else-if="details.albums.length"
        class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      >
        <ReleaseCard
          v-for="album in details.albums"
          :key="album.album_id || album.url"
          :release="album"
        />
      </div>

      <div v-else class="border-b-2 border-line p-4">
        <UiEmpty icon="search" :title="t('link.empty')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch as watchValue } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import TrackDownPlayHeader from '/src/components/library/TrackDownPlayHeader.vue'
import DownloadState from '/src/components/search/DownloadState.vue'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import SongPlayCell from '/src/components/library/SongPlayCell.vue'
import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import {
  jobSongKey,
  useDownloadManager,
  useProgressTracker,
} from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { classifyInput } from '/src/lib/input'
import { playableQueue } from '/src/lib/topSongs'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const library = useLibrary()
const ui = useUi()

const details = ref(null)
const loading = ref(false)
const error = ref('')
const submitting = ref(false)
const watching = ref(false)
const filter = ref('all')
const selected = ref(new Set())

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))
// The resolver field mirrors the address on screen, and hands a new one to
// the route (?url=) - the same contract this page has always had.
const urlInput = ref(url.value)

function submitUrl() {
  const next = urlInput.value.trim()
  if (!next || next === url.value) return
  router.replace({ name: 'Link', query: { url: next } })
}

async function resolve() {
  if (!url.value) return
  loading.value = true
  error.value = ''
  details.value = null
  selected.value = new Set()
  filter.value = 'all'
  try {
    const res = await API.resolveUrl(url.value)
    details.value = res.data
    library.lookupSongs(res.data?.tracks || [])
  } catch (err) {
    error.value = friendlyError(t, err, 'link.failed')
  } finally {
    loading.value = false
  }
}

watchValue(
  url,
  (value) => {
    urlInput.value = value
    resolve()
  },
  { immediate: true }
)

const SOURCE_LABELS = {
  spotify: () => t('link.openSpotify'),
  youtube: () => t('link.openYoutube'),
  deezer: () => t('link.openDeezer'),
}
const sourceLabel = computed(() =>
  (SOURCE_LABELS[kind.value.source] || SOURCE_LABELS.youtube)()
)

const kicker = computed(() => {
  const names = {
    spotify: 'Spotify',
    youtube: 'YouTube Music',
    deezer: 'Deezer',
  }
  const source = names[kind.value.source] || kind.value.source
  return `${source} · ${t(`link.kind.${details.value?.kind || 'track'}`)}`
})

// Playing a downloaded song from here queues the list's other downloaded
// songs after it, in the list's order; the rest play their preview clip.
const playQueue = computed(() =>
  playableQueue(details.value?.tracks || [], library.findTrack)
)
const playContext = computed(() =>
  details.value
    ? {
        type: details.value.kind === 'playlist' ? 'playlist' : 'album',
        title: details.value.name || '',
        subtitle: details.value.subtitle || '',
        cover: details.value.cover_url || '',
        route: { name: 'Link', query: { url: url.value } },
      }
    : null
)

// Playlist Monitor has no Deezer support: watching a Deezer playlist or
// artist for updates isn't offered, only downloading what's there now.
const watchable = computed(
  () =>
    (details.value?.kind === 'playlist' || details.value?.kind === 'artist') &&
    kind.value.source !== 'deezer'
)

const mosaic = computed(() =>
  [
    ...new Set(
      (details.value?.tracks || [])
        .map((song) => song.cover_url)
        .filter(Boolean)
    ),
  ].slice(0, 4)
)

const lengthLabel = computed(() => {
  const total = (details.value?.tracks || []).reduce(
    (sum, song) => sum + (song.duration || 0),
    0
  )
  if (!total) return ''
  const { hours, minutes } = splitLength(total)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})

function keyOf(song, index) {
  return jobSongKey(song) || `row-${index}`
}

function statusOf(song) {
  tracker.queueVersion.value
  if (tracker.getBySong(song)) return 'queue'
  const artist = (song.artists || [])[0] || song.artist
  return library.hasSong(artist, song.name) ? 'library' : 'new'
}

const rows = computed(() =>
  (details.value?.tracks || []).map((song, index) => ({
    song,
    index,
    key: keyOf(song, index),
    status: statusOf(song),
  }))
)

const newSongs = computed(() =>
  rows.value.filter((row) => row.status === 'new').map((row) => row.song)
)

const filters = computed(() => {
  const count = (status) =>
    rows.value.filter((row) => row.status === status).length
  return [
    { id: 'all', label: t('link.filterAll'), count: rows.value.length },
    { id: 'new', label: t('link.filterNew'), count: count('new') },
    { id: 'library', label: t('link.filterLibrary'), count: count('library') },
    { id: 'queue', label: t('link.filterQueue'), count: count('queue') },
  ].filter((item) => item.id === 'all' || item.count)
})

const visibleRows = computed(() =>
  filter.value === 'all'
    ? rows.value
    : rows.value.filter((row) => row.status === filter.value)
)

const selectedSongs = computed(() =>
  rows.value.filter((row) => selected.value.has(row.key)).map((row) => row.song)
)

function toggle(key) {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

async function download(songs) {
  if (!songs.length) return
  submitting.value = true
  try {
    const isPlaylist = details.value.kind === 'playlist'
    // Keep the playlist's own order for the M3U even when only some
    // tracks are sent.
    const withOrder = songs.map((song) => ({
      ...song,
      downtify_track_order: details.value.tracks.indexOf(song),
    }))
    const count = await dm.fromSongs(withOrder, {
      playlistUrl: isPlaylist ? url.value : '',
    })
    selected.value = new Set()
    ui.toast(t('toast.queuedTracks', { count, name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.queue'),
        run: () => router.push({ name: 'Queue' }),
      },
    })
  } catch (err) {
    ui.toast(friendlyError(t, err, 'toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    submitting.value = false
  }
}

async function watch() {
  watching.value = true
  try {
    await monitorAPI.addMonitoredPlaylist(url.value, 360)
    ui.toast(t('toast.watching', { name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.monitor'),
        run: () =>
          router.push({
            name: 'Monitor',
            params: {
              tab: details.value.kind === 'artist' ? 'artists' : 'playlists',
            },
          }),
      },
    })
  } catch (err) {
    ui.toast(friendlyError(t, err, 'toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    watching.value = false
  }
}
</script>
