<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('library.title')"
      :subtitle="summary"
      class="border-b-2 border-line"
    >
      <UiButton
        v-if="library.trackCount.value"
        variant="secondary"
        icon="wand"
        :to="{ name: 'Upgrade' }"
      >
        <span class="max-sm:sr-only">{{ t('library.upgrade') }}</span>
      </UiButton>
      <UiButton
        v-if="auth.isAdmin.value"
        variant="secondary"
        icon="library"
        :to="{ name: 'LibraryHealth' }"
      >
        <span class="max-sm:sr-only">{{ t('libraryHealth.title') }}</span>
      </UiButton>
      <UiButton
        v-if="auth.isAdmin.value && trashCapability.canManage.value"
        variant="secondary"
        icon="trash"
        :to="{ name: 'Trash' }"
      >
        <span class="max-sm:sr-only">{{ t('trash.title') }}</span>
      </UiButton>
      <UiButton
        variant="secondary"
        icon="refresh"
        :loading="library.loading.value"
        @click="library.load({ force: true })"
      >
        <span class="max-sm:sr-only">{{ t('common.refresh') }}</span>
      </UiButton>
    </PageHeader>

    <UiTabs :items="tabs" :model-value="tab" />

    <!-- Archive filters: one ruled strip, each control a block. -->
    <div
      class="flex flex-wrap items-center gap-2 px-4 py-2"
      :class="showFormatChips ? '' : 'border-b-2 border-line'"
    >
      <label
        class="flex h-9 min-w-0 flex-1 basis-48 items-center gap-2 border-2 border-line-2 px-2.5 transition-colors duration-100 focus-within:border-accent sm:max-w-xs"
      >
        <AppIcon name="filter" :size="15" class="text-faint" />
        <span class="sr-only">{{ t('library.filterPlaceholder') }}</span>
        <input
          v-model="filter"
          type="search"
          :placeholder="t('library.filterPlaceholder')"
          class="h-full min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint"
        />
      </label>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <UiButton
          v-if="tab === 'playlists' && auth.isAdmin.value"
          variant="primary"
          icon="plus"
          @click="playlistActions.openCreate()"
        >
          {{ t('playlists.create') }}
        </UiButton>
        <UiSelect
          v-if="tab !== 'tracks'"
          v-model="sortKey"
          :options="sortOptions"
          :label="t('library.sortBy')"
          icon="sort"
          size="sm"
        />
        <UiSegmented
          v-if="tab !== 'tracks'"
          v-model="view"
          :options="[
            { value: 'grid', icon: 'grid', label: t('library.viewGrid') },
            { value: 'list', icon: 'list', label: t('library.viewList') },
          ]"
        />
      </div>
    </div>

    <!-- Format filter: its own ruled strip, so the chips' frames read as the
         rules above and below. -->
    <UiChips
      v-if="showFormatChips"
      v-model="format"
      :items="formatChips"
      class="px-3 pb-1"
    />

    <!-- Loading -->
    <Transition name="fade" mode="out-in">
    <div
      v-if="!catalogReady && library.loading.value"
      class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6"
    >
      <div
        v-for="n in 12"
        :key="n"
        class="flex flex-col gap-2 border-r-2 border-b-2 border-line p-2"
      >
        <UiSkeleton class="aspect-square" />
        <UiSkeleton class="h-3 w-3/4" />
        <UiSkeleton class="h-2.5 w-1/2" />
      </div>
    </div>

    <div
      v-else-if="library.error.value && !library.trackCount.value"
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="alert"
        :title="t('library.loadFailed')"
        :body="t('library.loadFailedHint')"
      >
        <UiButton icon="refresh" @click="library.load({ force: true })">
          {{ t('common.retry') }}
        </UiButton>
      </UiEmpty>
    </div>

    <div
      v-else-if="
        tab !== 'playlists' &&
        !library.trackCount.value &&
        !library.playlists.value.length
      "
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="library"
        :title="t('library.emptyTitle')"
        :body="t('library.emptyBody')"
      >
        <UiButton variant="primary" icon="search" @click="ui.focusSearch()">
          {{ t('library.emptyAction') }}
        </UiButton>
      </UiEmpty>
    </div>

    <div
      v-else-if="!items.length && !(tab === 'playlists' && !filter)"
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="filter"
        :title="t('library.noMatches')"
        :body="t('library.noMatchesHint')"
      >
        <UiButton variant="ghost" @click="clearFilters">{{
          t('library.clearFilters')
        }}</UiButton>
      </UiEmpty>
    </div>

    <!-- Tracks -->
    <div v-else-if="tab === 'tracks'" class="flex min-w-0 flex-col">
      <SelectionBar
        :count="selectedCount"
        :total="items.length"
        :zipping="zipping"
        @select-all="selectAll"
        @clear="clear"
        @play="playSelected"
        @enqueue="enqueueSelected"
        @zip="zipSelected"
        @delete="deleteSelected"
        @add-to-playlist="addSelectedToPlaylist"
      />
      <div class="flex flex-wrap items-center gap-2 px-4 py-2.5">
        <UiButton
          variant="primary"
          icon="play"
          @click="actions.play(items, 0, libraryContext)"
        >
          {{ t('actions.playAll') }}
        </UiButton>
        <UiButton
          variant="secondary"
          icon="shuffle"
          @click="actions.play(items, 0, libraryContext, { shuffled: true })"
        >
          {{ t('actions.shuffle') }}
        </UiButton>
        <span class="mono ml-auto text-muted">
          {{ t('common.tracks', { count: items.length }) }}
        </span>
      </div>
      <TrackList
        v-model:selected="selected"
        v-model:sort="trackSort"
        :tracks="items"
        :context="libraryContext"
      />
    </div>

    <!-- Albums / artists / playlists: flush grid -->
    <div
      v-else-if="view === 'grid'"
      class="stagger grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6 min-[1900px]:grid-cols-7"
    >
      <MediaTile
        v-for="item in items"
        :key="item.key"
        v-bind="tileProps(item)"
        class="[contain-intrinsic-size:auto_260px] [content-visibility:auto]"
        @play="playItem(item)"
      >
        <template
          v-if="tab === 'playlists' && item.batch?.missing_count"
          #badge
        >
          <span
            class="mono absolute right-0 bottom-0 border-l-2 border-t-2 border-line bg-warn px-1.5 py-0.5 text-[10px] text-bg"
          >
            {{
              t('playlists.missingShort', { count: item.batch.missing_count })
            }}
          </span>
        </template>
      </MediaTile>
    </div>

    <!-- Albums / artists / playlists: ruled list -->
    <div v-else class="stagger border-x-2 border-b-2 border-line">
      <MediaRow
        v-for="item in items"
        :key="item.key"
        v-bind="tileProps(item)"
        :aside="asideFor(item)"
        class="[contain-intrinsic-size:auto_72px] [content-visibility:auto]"
        @play="playItem(item)"
      >
        <template v-if="tab === 'playlists'" #meta>
          <PlaylistStatus :playlist="item" class="w-56" />
        </template>
        <template v-if="tab === 'playlists'" #actions>
          <UiMenu
            :items="playlistMenu(item)"
            :label="t('common.more')"
            size="sm"
          />
        </template>
      </MediaRow>
    </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import MediaRow from '/src/components/library/MediaRow.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import PlaylistStatus from '/src/components/library/PlaylistStatus.vue'
import SelectionBar from '/src/components/library/SelectionBar.vue'
import TrackList from '/src/components/library/TrackList.vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useAuth } from '/src/model/auth'
import { useTrackActions } from '/src/model/trackActions'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackSelection } from '/src/model/selection'
import { useUi } from '/src/model/ui'
import {
  albumKey,
  artistKey,
  filterItems,
  itemTrackCount,
  sortItems,
} from '/src/lib/library'
import { artistPhotoSource } from '/src/lib/artistPhotoProxy'
import { formatBytes, splitLength } from '/src/lib/format'
import { useTrashCapability } from '/src/lib/trash'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const auth = useAuth()
const actions = useTrackActions()
const trashCapability = useTrashCapability()
const playlistActions = usePlaylistActions()
const ui = useUi()

const TABS = ['albums', 'artists', 'playlists', 'tracks']
const lastTab = useLocalStorage('downtify-library-tab', 'albums')
const tab = computed(() => {
  const requested = String(route.params.tab || '')
  return TABS.includes(requested) ? requested : lastTab.value
})
watch(tab, (value) => (lastTab.value = value), { immediate: true })
if (!route.params.tab) {
  router.replace({ name: 'Library', params: { tab: tab.value } })
}

function loadTab(current) {
  if (current === 'tracks') library.ensureTracks()
  else if (current === 'albums') library.ensureAlbums()
  else if (current === 'artists') library.ensureArtists()
}

onMounted(() => loadTab(tab.value))
watch(tab, (value) => loadTab(value))

const catalogReady = computed(() => {
  if (tab.value === 'tracks') return library.tracksComplete.value
  if (tab.value === 'albums') {
    return library.albumsComplete.value || library.tracksComplete.value
  }
  if (tab.value === 'artists') {
    return library.artistsComplete.value || library.tracksComplete.value
  }
  return library.loaded.value
})

// Artist photos saved via the artist page's picker (see artist_profile.py)
// - fetched once per visit to the artists tab so tiles use the real photo
// instead of a track's cover when one has been picked. Falls back to
// today's behaviour (a track cover) for any artist without one.
const artistPhotos = ref({})
// Whether the lookup above has answered - until it has, an artist might
// still turn out to have a saved photo, so no proxy request is made yet.
const artistPhotosLoaded = ref(false)
watch(
  // Re-fires when the tab switches to artists, and again once the
  // library finishes loading if it hadn't yet (e.g. a direct page load
  // on this tab, where artists.value starts out empty).
  () => [tab.value, library.artists.value.length],
  async ([currentTab]) => {
    if (currentTab !== 'artists') return
    const names = library.artists.value.map((artist) => artist.name)
    if (!names.length) return
    try {
      const res = await API.getArtistArtBulk(names)
      artistPhotos.value = res.data || {}
    } catch {
      artistPhotos.value = {}
    }
    artistPhotosLoaded.value = true
  },
  { immediate: true }
)

// An artist's picture on the artists tab: their saved photo when there is
// one; otherwise the display-only photo from the backend's proxy (see
// lib/artistPhotoProxy.js), with the track's own cover behind it for an
// artist the proxy has no photo for. Only this tab - the search page's
// artists come with their own picture and never go through here.
function artistCover(item) {
  return artistPhotoSource(
    item.name,
    artistPhotos.value[item.name],
    artistPhotosLoaded.value,
    item.cover
  )
}

const views = useLocalStorage('downtify-library-views', {
  albums: 'grid',
  artists: 'grid',
  playlists: 'grid',
})
const view = computed({
  get: () => views.value[tab.value] || 'grid',
  set: (value) => (views.value = { ...views.value, [tab.value]: value }),
})

const sorts = useLocalStorage('downtify-library-sorts', {
  albums: 'added',
  artists: 'title',
  playlists: 'added',
})
const sortKey = computed({
  get: () => sorts.value[tab.value] || 'added',
  set: (value) => (sorts.value = { ...sorts.value, [tab.value]: value }),
})
const trackSort = useLocalStorage('downtify-library-track-sort', {
  key: 'added',
  dir: 'asc',
})

const filter = ref('')
const format = ref('all')
const selection = useTrackSelection({
  tracks: () => items.value,
  resetKey: () => tab.value,
  context: () => libraryContext.value,
})
const {
  selected,
  count: selectedCount,
  zipping,
  selectAll,
  clear,
  playSelected,
  enqueueSelected,
  zipSelected,
  deleteSelected,
  addSelectedToPlaylist,
} = selection
watch(tab, () => {
  filter.value = ''
  format.value = 'all'
})

const tabs = computed(() => [
  {
    id: 'albums',
    label: t('library.albums'),
    count: library.albumCount.value,
    to: { name: 'Library', params: { tab: 'albums' } },
  },
  {
    id: 'artists',
    label: t('library.artists'),
    count: library.artistCount.value,
    to: { name: 'Library', params: { tab: 'artists' } },
  },
  {
    id: 'playlists',
    label: t('library.playlists'),
    count: library.playlists.value.length,
    to: { name: 'Library', params: { tab: 'playlists' } },
  },
  {
    id: 'tracks',
    label: t('library.tracks'),
    count: library.trackCount.value,
    to: { name: 'Library', params: { tab: 'tracks' } },
  },
])

const summary = computed(() => {
  if (!library.loaded.value) return ''
  return [
    t('common.tracks', { count: library.trackCount.value }),
    t('common.albums', { count: library.albumCount.value }),
    t('common.artists', { count: library.artistCount.value }),
    formatBytes(library.totalSize.value),
  ].join(' · ')
})

const sortOptions = computed(() => {
  const base = [
    { value: 'added', label: t('library.sortRecent') },
    { value: 'title', label: t('library.sortName') },
  ]
  if (tab.value === 'albums') {
    base.push(
      { value: 'artist', label: t('library.sortArtist') },
      { value: 'year', label: t('library.sortYear') }
    )
  }
  base.push({ value: 'count', label: t('library.sortTrackCount') })
  return base
})

const showFormatChips = computed(
  () => tab.value === 'tracks' && formatChips.value.length > 2
)

const formatChips = computed(() => {
  const counts = new Map()
  for (const track of library.tracks.value) {
    counts.set(track.format, (counts.get(track.format) || 0) + 1)
  }
  return [
    { id: 'all', label: t('library.allFormats') },
    ...[...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([id, count]) => ({ id, label: id, count })),
  ]
})

const items = computed(() => {
  if (tab.value === 'tracks') {
    let list = library.tracks.value
    if (format.value !== 'all') {
      list = list.filter((track) => track.format === format.value)
    }
    list = filterItems(list, filter.value, ['title', 'artist', 'album', 'file'])
    return sortItems(list, trackSort.value.key, trackSort.value.dir)
  }
  if (tab.value === 'albums') {
    return sortItems(
      filterItems(library.albums.value, filter.value, [
        'title',
        'artist',
        'year',
      ]),
      sortKey.value
    )
  }
  if (tab.value === 'artists') {
    return sortItems(
      filterItems(library.artists.value, filter.value, ['name']),
      sortKey.value
    )
  }
  return sortItems(
    filterItems(library.playlists.value, filter.value, ['title', 'name']),
    sortKey.value
  )
})

const libraryContext = computed(() => ({
  type: 'library',
  title: t('library.allTracks'),
  route: { name: 'Library', params: { tab: 'tracks' } },
}))

const current = computed(() => player.currentTrack.value)

function tileProps(item) {
  if (tab.value === 'albums') {
    return {
      to: { name: 'Album', query: { artist: item.artist, title: item.title } },
      title: item.title,
      subtitle: [
        item.artist,
        item.year,
        item.tracks?.length
          ? t('common.tracks', { count: item.tracks.length })
          : '',
        item.size ? formatBytes(item.size) : '',
      ]
        .filter(Boolean)
        .join(' · '),
      cover: item.cover,
      name: item.title,
      icon: 'disc',
      playing:
        !!current.value &&
        albumKey(current.value.albumArtist, current.value.album) === item.key,
    }
  }
  if (tab.value === 'artists') {
    return {
      to: { name: 'Artist', query: { name: item.name } },
      title: item.name,
      subtitle: [
        item.albums.length
          ? t('common.albums', { count: item.albums.length })
          : item.albumCount
            ? t('common.albums', { count: item.albumCount })
            : '',
        t('common.tracks', {
          count: itemTrackCount(item),
        }),
      ]
        .filter(Boolean)
        .join(' · '),
      ...artistCover(item),
      name: item.name,
      icon: 'user',
      round: true,
      playing:
        !!current.value && artistKey(current.value.albumArtist) === item.key,
    }
  }
  return {
    to: { name: 'Playlist', query: { name: item.name } },
    title: item.title,
    subtitle: playlistSubtitle(item),
    cover: item.cover,
    covers: item.covers,
    name: item.title,
    icon: item.liked ? 'heart' : 'playlist',
    symbol: item.liked,
    playable: itemTrackCount(item) > 0,
    playing:
      player.context.value?.type === 'playlist' &&
      player.context.value?.title === item.title,
  }
}

function playlistSubtitle(item) {
  const batch = item.batch
  if (batch?.expected_count) {
    return t('playlists.progress', {
      have: batch.downloaded_count,
      total: batch.expected_count,
    })
  }
  return t('common.tracks', { count: itemTrackCount(item) })
}

function asideFor(item) {
  const { hours, minutes } = splitLength(item.duration)
  if (!hours && !minutes) return ''
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
}

async function playItem(item) {
  if (tab.value === 'albums') {
    await library.loadArtistTracks(item.artist)
    const album = library.findAlbum(item.artist, item.title)
    const list = album?.tracks || []
    if (!list.length) return
    actions.play(list, 0, {
      type: 'album',
      title: item.title,
      subtitle: item.artist,
      cover: item.cover,
      route: {
        name: 'Album',
        query: { artist: item.artist, title: item.title },
      },
    })
  } else if (tab.value === 'artists') {
    await library.loadArtistTracks(item.name)
    const artist = library.findArtist(item.name)
    const list = artist?.tracks || []
    if (!list.length) return
    actions.play(
      list,
      0,
      {
        type: 'artist',
        title: item.name,
        cover: item.cover,
        route: { name: 'Artist', query: { name: item.name } },
      },
      { shuffled: true }
    )
  } else {
    await library.loadPlaylistTracks(item.name)
    const live = library.findPlaylist(item.name)
    const list = live?.tracks || []
    if (!list.length) return
    actions.play(list, 0, playlistActions.contextFor(live || item))
  }
}

function playlistMenu(item) {
  return playlistActions.menuFor(item)
}

function clearFilters() {
  filter.value = ''
  format.value = 'all'
}
</script>
