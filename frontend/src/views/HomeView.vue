<template>
  <div class="flex flex-col">
    <!-- Entry block: the greeting, the paste-or-search field, and the
         sources it understands. -->
    <section
      class="flex flex-col gap-4 border-b-2 border-line px-4 py-5 sm:px-6"
    >
      <div
        class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"
      >
        <div class="min-w-0">
          <h1
            class="text-display text-[26px] leading-[1.05] font-bold tracking-[-0.02em] sm:text-[34px]"
          >
            {{ greeting }}
          </h1>
          <p class="mt-2 max-w-lg text-[13px] text-pretty text-muted">
            {{ t('home.lead') }}
          </p>
        </div>
        <form
          class="flex w-full min-w-0 flex-col gap-2 sm:flex-row lg:max-w-2xl"
          @submit.prevent="submit"
        >
          <label
            class="flex h-12 min-w-0 flex-1 items-center gap-2 border-2 px-3 transition-colors duration-100 focus-within:border-accent"
            :class="kind.type === 'link' ? 'border-accent' : 'border-line'"
          >
            <AppIcon
              :name="kind.type === 'link' ? 'link' : 'search'"
              :size="16"
              :class="kind.type === 'link' ? 'text-accent' : 'text-faint'"
            />
            <span class="sr-only">{{ t('home.inputLabel') }}</span>
            <input
              v-model="text"
              type="text"
              enterkeyhint="go"
              autocomplete="off"
              :placeholder="t('home.inputPlaceholder')"
              class="h-full min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-faint"
            />
          </label>
          <UiButton
            type="submit"
            variant="primary"
            size="lg"
            :icon="kind.type === 'link' ? 'download' : 'search'"
            :disabled="kind.type === 'empty'"
          >
            {{
              kind.type === 'link' ? t('home.getIt') : t('search.searchButton')
            }}
          </UiButton>
        </form>
      </div>
      <p v-if="unsupported" class="text-[12px] text-danger">
        {{ unsupported }}
      </p>
      <div
        class="flex flex-wrap items-center gap-x-5 gap-y-1.5 border-t border-line-2 pt-3"
      >
        <span class="eyebrow flex items-center gap-1.5">
          <AppIcon name="spotify" :size="13" />{{ t('home.hintSpotify') }}
        </span>
        <span class="eyebrow flex items-center gap-1.5">
          <AppIcon name="youtube" :size="13" />{{ t('home.hintYoutube') }}
        </span>
        <span class="eyebrow flex items-center gap-1.5">
          <AppIcon name="deezer" :size="13" />{{ t('home.hintDeezer') }}
        </span>
        <button
          type="button"
          class="eyebrow flex items-center gap-1.5 transition-colors duration-100 hover:text-fg"
          @click="csvPicker?.click()"
        >
          <AppIcon name="file-music" :size="13" />{{ t('home.hintCsv') }}
        </button>
        <input
          ref="csvPicker"
          type="file"
          accept=".csv,text/csv"
          class="hidden"
          @change="importCsv"
        />
      </div>
    </section>

    <!-- First run: three numbered blocks -->
    <section
      v-if="library.loaded.value && !library.trackCount.value"
      class="grid border-b-2 border-line md:grid-cols-3"
    >
      <div
        v-for="(step, i) in onboarding"
        :key="step.title"
        class="flex flex-col gap-2 border-b-2 border-line p-4 md:border-r-2 md:border-b-0 md:last:border-r-0 transition-colors duration-200 hover:bg-surface-2 motion-reduce:transition-none"
      >
        <span class="mono tabular text-faint">0{{ i + 1 }}</span>
        <p class="text-display text-[15px] font-bold">{{ step.title }}</p>
        <p class="text-[13px] text-pretty text-muted">{{ step.body }}</p>
      </div>
    </section>

    <div class="grid xl:grid-cols-[minmax(0,1fr)_360px]">
      <div class="flex min-w-0 flex-col">
        <!-- Continue listening -->
        <section v-if="jumpBackIn.length" class="flex flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <span
              class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
              >01</span
            >
            <h2
              class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
            >
              {{ t('home.jumpBackIn') }}
            </h2>
            <span
              class="mono hidden items-center border-l-2 border-line px-3 text-faint sm:flex"
              >{{ jumpBackIn.length }}</span
            >
          </div>
          <div
            class="stagger grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 lg:grid-cols-5"
          >
            <MediaTile
              v-for="entry in jumpBackIn"
              :key="entry.id"
              :to="entry.route || { name: 'Home' }"
              :title="entry.title"
              :subtitle="entry.subtitle || t(`home.kind.${entry.type}`)"
              :cover="entry.cover"
              :covers="entry.covers"
              :name="entry.title"
              :icon="
                entry.type === 'artist'
                  ? 'user'
                  : entry.type === 'playlist'
                    ? 'playlist'
                    : 'disc'
              "
              :playing="isPlaying(entry)"
              :playable="false"
            >
              <template #badge>
                <span
                  class="eyebrow absolute top-0 right-0 border-b-2 border-l-2 border-line bg-surface px-1.5 py-0.5 text-fg-3"
                  >{{ t(`home.kind.${entry.type}`) }}</span
                >
              </template>
            </MediaTile>
          </div>
        </section>

        <!-- Recently added: ruled table -->
        <section v-if="recentAlbums.length" class="flex flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <span
              class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
              >02</span
            >
            <h2
              class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
            >
              {{ t('home.recentlyAdded') }}
            </h2>
            <RouterLink
              :to="{ name: 'Library', params: { tab: 'albums' } }"
              class="eyebrow flex items-center border-l-2 border-line px-3 text-muted transition-colors duration-100 hover:text-fg"
              >{{ t('common.seeAll') }}</RouterLink
            >
          </div>
          <div class="stagger border-l-2 border-line">
            <div
              class="eyebrow grid h-8 items-center gap-3 border-b border-line-2 bg-surface-2 px-3 max-md:hidden md:grid-cols-[32px_minmax(0,2fr)_minmax(0,1.4fr)_72px_80px_88px]"
            >
              <span class="text-center">#</span>
              <span>{{ t('track.title') }}</span>
              <span>{{ t('track.artist') }}</span>
              <span>{{ t('track.year') }}</span>
              <span class="text-right">{{ t('library.tracks') }}</span>
              <span class="text-right">{{ t('home.size') }}</span>
            </div>
            <RouterLink
              v-for="(album, i) in recentAlbums"
              :key="album.key"
              :to="{
                name: 'Album',
                query: { artist: album.artist, title: album.title },
              }"
              class="mono grid min-h-12 grid-cols-[minmax(0,1fr)_88px] items-center gap-3 border-r-2 border-b border-line-2 px-3 transition-colors duration-100 last:border-b-0 hover:bg-surface-2 md:grid-cols-[32px_minmax(0,2fr)_minmax(0,1.4fr)_72px_80px_88px]"
            >
              <span class="tabular hidden text-center text-faint md:block">{{
                String(i + 1).padStart(2, '0')
              }}</span>
              <span
                class="flex min-w-0 flex-col gap-0.5 md:flex-row md:items-center md:gap-2"
              >
                <span
                  class="min-w-0 truncate text-display text-[13px] font-bold text-fg"
                  >{{ album.title }}</span
                >
                <span
                  v-if="album.key === currentAlbumKey"
                  class="eyebrow shrink-0 self-start border border-accent px-1 text-accent"
                  >{{ t('player.playing') }}</span
                >
                <span class="truncate text-muted md:hidden">{{
                  album.artist
                }}</span>
              </span>
              <span class="truncate text-muted max-md:hidden">{{
                album.artist
              }}</span>
              <span class="tabular hidden text-muted md:block">{{
                album.year || '—'
              }}</span>
              <span class="tabular hidden text-right text-muted md:block">{{
                album.tracks?.length || 0
              }}</span>
              <span class="tabular truncate text-right text-fg-3 md:block">{{
                formatBytes(album.size)
              }}</span>
            </RouterLink>
          </div>
        </section>

        <!-- Your playlists -->
        <section v-if="recentPlaylists.length" class="flex flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <span
              class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
              >03</span
            >
            <h2
              class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
            >
              {{ t('home.playlists') }}
            </h2>
            <RouterLink
              :to="{ name: 'Library', params: { tab: 'playlists' } }"
              class="eyebrow flex items-center border-l-2 border-line px-3 text-muted transition-colors duration-100 hover:text-fg"
              >{{ t('common.seeAll') }}</RouterLink
            >
          </div>
          <div
            class="stagger grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 lg:grid-cols-5"
          >
            <MediaTile
              v-for="playlist in recentPlaylists"
              :key="playlist.key"
              :to="{ name: 'Playlist', query: { name: playlist.name } }"
              :title="playlist.title"
              :subtitle="
                t('common.tracks', { count: itemTrackCount(playlist) })
              "
              :cover="playlist.cover"
              :covers="playlist.covers"
              :name="playlist.title"
              :icon="playlist.liked ? 'heart' : 'playlist'"
              :symbol="playlist.liked"
              :playing="
                player.context.value?.type === 'playlist' &&
                player.context.value?.title === playlist.title
              "
              @play="playlistActions.play(playlist)"
            />
          </div>
        </section>
      </div>

      <!-- Apparatus column: download queue, up next, most played, storage -->
      <aside
        class="flex min-w-0 flex-col xl:-ml-0.5 xl:border-l-2 xl:border-line"
      >
        <UiPanel
          v-if="pending"
          :title="t('home.downloading')"
          class="-mt-0.5 first:mt-0"
        >
          <template #actions>
            <UiButton
              variant="ghost"
              size="sm"
              icon-right="chevron-right"
              :to="{ name: 'Queue' }"
            >
              {{ t('home.openQueue') }}
            </UiButton>
          </template>
          <ul class="flex flex-col gap-3">
            <li
              v-for="item in activeItems"
              :key="item.key"
              class="flex items-center gap-3"
            >
              <CoverArt
                :src="item.song.cover_url"
                :name="item.song.album_name || item.song.name"
                :letter-size="11"
                :icon-size="14"
                class="size-9"
              />
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between gap-2">
                  <span class="min-w-0 truncate text-[13px] font-semibold">{{
                    item.song.name
                  }}</span>
                  <SourceBadge
                    v-if="item.provider"
                    :source="item.provider"
                    compact
                  />
                </div>
                <UiProgress
                  class="mt-2"
                  :value="item.progress"
                  :indeterminate="!item.progress"
                />
              </div>
            </li>
          </ul>
          <p v-if="waiting" class="mono mt-3 text-faint">
            {{ t('home.waiting', { count: waiting }) }}
          </p>
        </UiPanel>

        <UiPanel
          v-if="upNext.length"
          :title="t('player.upNext')"
          class="-mt-0.5 first:mt-0"
        >
          <ul class="stagger flex flex-col">
            <li
              v-for="(entry, i) in upNext"
              :key="entry.track.file || i"
              class="flex items-center gap-3 border-b border-line-2 py-2 first:pt-0 last:border-b-0 last:pb-0"
            >
              <CoverArt
                :src="entry.track.cover"
                :name="entry.track.album || entry.track.title"
                :letter-size="10"
                :icon-size="13"
                class="size-8"
              />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[13px] font-semibold">{{
                  entry.track.title
                }}</span>
                <span class="mono block truncate text-muted">{{
                  entry.track.artist
                }}</span>
              </span>
              <span class="mono tabular shrink-0 text-faint">{{
                entry.track.duration ? formatDuration(entry.track.duration) : ''
              }}</span>
            </li>
          </ul>
        </UiPanel>

        <UiPanel
          v-if="mostPlayed.length"
          :title="t('stats.topTracks')"
          class="-mt-0.5 first:mt-0"
        >
          <ol class="stagger flex flex-col">
            <li
              v-for="(row, i) in mostPlayed"
              :key="row.summary"
              class="flex items-center gap-3 border-b border-line-2 py-2 first:pt-0 last:border-b-0 last:pb-0"
            >
              <span class="mono tabular w-5 shrink-0 text-faint">{{
                String(i + 1).padStart(2, '0')
              }}</span>
              <span class="min-w-0 flex-1 truncate text-[13px]">{{
                row.summary
              }}</span>
              <span class="mono tabular shrink-0 text-muted">{{
                row.count
              }}</span>
            </li>
          </ol>
        </UiPanel>

        <UiPanel :title="t('settings.storage')" class="-mt-0.5 first:mt-0">
          <dl class="mb-3 grid grid-cols-3 gap-2 border-b border-line-2 pb-3">
            <div v-for="stat in counts" :key="stat.label" class="min-w-0">
              <dt class="eyebrow truncate">{{ stat.label }}</dt>
              <dd
                v-count-up
                class="mono tabular stat-reveal mt-0.5 text-[14px] text-fg"
              >
                {{ stat.value }}
              </dd>
            </div>
          </dl>
          <dl class="flex flex-col gap-1">
            <div class="flex items-baseline justify-between gap-3">
              <dt class="eyebrow">{{ t('home.size') }}</dt>
              <dd class="mono tabular text-[13px] text-fg">
                {{ formatBytes(library.totalSize.value) }}
              </dd>
            </div>
          </dl>
          <div class="mt-3 flex h-3 gap-0.5" aria-hidden="true">
            <span
              v-for="(row, i) in storageByFormat"
              :key="row.format"
              class="min-w-0"
              :class="i === 0 ? 'bg-fg' : 'bg-line-3'"
              :style="{ flexGrow: Math.max(row.size, 1) }"
            />
          </div>
          <ul class="mt-3 flex flex-col">
            <li
              v-for="row in storageByFormat"
              :key="row.format"
              class="mono flex items-center justify-between gap-3 border-b border-line-2 py-1.5 last:border-b-0"
            >
              <span class="text-muted">{{ row.format }}</span>
              <span class="tabular text-fg-3">{{ formatBytes(row.size) }}</span>
            </li>
            <li v-if="!storageByFormat.length" class="mono py-1.5 text-faint">
              {{ t('stats.empty') }}
            </li>
          </ul>
          <UiButton
            variant="secondary"
            icon-right="chevron-right"
            :to="{ name: 'Library' }"
            class="mt-3 w-full"
          >
            {{ t('home.openLibrary') }}
          </UiButton>
        </UiPanel>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import SourceBadge from '/src/components/ui/SourceBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useHistory } from '/src/model/history'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useStats } from '/src/model/stats'
import { useUi } from '/src/model/ui'
import { classifyInput } from '/src/lib/input'
import { albumKey, itemTrackCount } from '/src/lib/library'
import { formatBytes, formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'
// Local registration: SSR renders this view without the app's directives.
import { countUpDirective as vCountUp } from '/src/composables/useCountUp'

const { t } = useI18n()
const router = useRouter()
const library = useLibrary()
const history = useHistory()
const player = usePlayer()
const tracker = useProgressTracker()
const dm = useDownloadManager()
const playlistActions = usePlaylistActions()
const statsStore = useStats()
const ui = useUi()

const text = ref('')
const unsupported = ref('')
const csvPicker = ref(null)
const kind = computed(() => classifyInput(text.value))

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 5) return t('home.greetingNight')
  if (hour < 12) return t('home.greetingMorning')
  if (hour < 18) return t('home.greetingAfternoon')
  return t('home.greetingEvening')
})

function submit() {
  unsupported.value = ''
  const result = kind.value
  if (result.type === 'link') {
    router.push({ name: 'Link', query: { url: result.url } })
  } else if (result.type === 'search') {
    router.push({ name: 'Search', params: { query: result.query } })
  } else if (result.type === 'unsupported') {
    unsupported.value = t('search.unsupportedLink')
  }
}

async function importCsv(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const result = await dm.fromCsvFile(file, file.name.replace(/\.csv$/i, ''))
    ui.toast(t('toast.csvQueued', { count: result?.count ?? 0 }), {
      kind: 'success',
    })
    router.push({ name: 'Queue', params: { tab: 'queued' } })
  } catch (err) {
    ui.toast(friendlyError(t, err, 'queue.importFailed'), {
      kind: 'error',
    })
  }
}

const queueItems = computed(() => {
  tracker.queueVersion.value
  return tracker.downloadQueue.value
})
const activeItems = computed(() =>
  queueItems.value.filter((item) => item.state === 'active').slice(0, 3)
)
const waiting = computed(
  () => queueItems.value.filter((item) => item.state === 'queued').length
)
const pending = computed(() => activeItems.value.length + waiting.value)

const recentAlbums = computed(() =>
  [...library.albums.value].sort((a, b) => b.added - a.added).slice(0, 7)
)
const recentPlaylists = computed(() =>
  [...library.playlists.value]
    .filter((playlist) => itemTrackCount(playlist))
    .sort((a, b) => b.added - a.added)
    .slice(0, 6)
)

const jumpBackIn = computed(() =>
  history.recent.value
    .map((entry) => {
      if (entry.type !== 'playlist') return entry
      const name = String(entry.route?.query?.name || entry.title || '')
      const live = library.findPlaylist(name)
      if (!live) return null
      return {
        ...entry,
        title: live.title,
        cover: live.cover || live.covers[0] || entry.cover || '',
        covers: live.covers,
        route: { name: 'Playlist', query: { name: live.name } },
      }
    })
    .filter(Boolean)
    .slice(0, 5)
)

function isPlaying(entry) {
  const ctx = player.context.value
  return (
    player.isPlaying.value &&
    ctx?.type === entry.type &&
    ctx?.title === entry.title
  )
}

const currentAlbumKey = computed(() =>
  player.currentTrack.value
    ? albumKey(
        player.currentTrack.value.albumArtist,
        player.currentTrack.value.album
      )
    : ''
)

const upNext = computed(() => player.upcoming.value.slice(0, 3))

// The play counts live in /stats; load them once if the Stats tab has not.
const mostPlayed = computed(() =>
  (statsStore.stats.value?.playback?.top_tracks || []).slice(0, 5)
)
onMounted(() => {
  if (!statsStore.stats.value?.playback) statsStore.load()
})

const counts = computed(() => [
  {
    label: t('library.tracks'),
    value: library.trackCount.value.toLocaleString(),
  },
  {
    label: t('library.albums'),
    value: library.albumCount.value.toLocaleString(),
  },
  {
    label: t('library.artists'),
    value: library.artistCount.value.toLocaleString(),
  },
])

const storageByFormat = computed(() => {
  const map = new Map()
  for (const track of library.tracks.value) {
    const entry = map.get(track.format) || {
      format: track.format,
      size: 0,
    }
    entry.size += track.size || 0
    map.set(track.format, entry)
  }
  return [...map.values()]
    .filter((row) => row.size > 0)
    .sort((a, b) => b.size - a.size)
    .slice(0, 4)
})

const onboarding = computed(() => [
  { title: t('home.step1Title'), body: t('home.step1Body') },
  { title: t('home.step2Title'), body: t('home.step2Body') },
  { title: t('home.step3Title'), body: t('home.step3Body') },
])
</script>
