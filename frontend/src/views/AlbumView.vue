<template>
  <div class="mx-auto flex w-full max-w-[1680px] flex-col">
    <DetailState
      :loaded="ready"
      :found="!!album"
      icon="disc"
      :missing="t('album.notFound')"
    >
      <CollectionHero
        :title="album.title"
        :kicker="[t('album.kicker'), album.year].filter(Boolean).join(' · ')"
        :cover="album.cover"
        :name="album.title"
      >
        <template #subtitle>
          <dl
            class="grid w-full grid-cols-1 border-t-2 border-l-2 border-line sm:grid-cols-2"
          >
            <div
              class="flex min-w-0 items-baseline gap-3 border-r-2 border-b-2 border-line px-2 py-1"
            >
              <dt class="eyebrow shrink-0">{{ t('track.artist') }}</dt>
              <dd class="min-w-0 truncate">
                <RouterLink
                  v-if="album.artist"
                  :to="{ name: 'Artist', query: { name: album.artist } }"
                  class="text-fg hover:underline"
                  >{{ album.artist }}</RouterLink
                >
              </dd>
            </div>
            <div
              class="flex min-w-0 items-baseline gap-3 border-r-2 border-b-2 border-line px-2 py-1"
            >
              <dt class="eyebrow shrink-0">{{ t('track.format') }}</dt>
              <dd class="min-w-0 truncate">{{ albumFormats }}</dd>
            </div>
            <div
              class="flex min-w-0 items-baseline gap-3 border-r-2 border-b-2 border-line px-2 py-1"
            >
              <dt class="eyebrow shrink-0">{{ t('track.year') }}</dt>
              <dd class="min-w-0 truncate">{{ album.year }}</dd>
            </div>
            <div
              class="flex min-w-0 items-baseline gap-3 border-r-2 border-b-2 border-line px-2 py-1"
            >
              <dt class="eyebrow shrink-0">{{ t('track.size') }}</dt>
              <dd class="min-w-0 truncate">{{ formatBytes(album.size) }}</dd>
            </div>
          </dl>
        </template>
        <template #actions>
          <PlayButton
            :label="t('actions.playItem', { name: album.title })"
            :playing="isThisPlaying"
            @click="togglePlay"
          />
          <UiIconButton
            icon="shuffle"
            :label="t('actions.shuffle')"
            size="lg"
            round
            @click="actions.play(album.tracks, 0, context, { shuffled: true })"
          />
          <UiButton
            variant="secondary"
            icon="queue"
            @click="actions.enqueue(album.tracks)"
          >
            {{ t('actions.addToQueue') }}
          </UiButton>
          <UiButton
            variant="secondary"
            icon="zip"
            class="max-sm:hidden"
            @click="actions.downloadZip(album.tracks)"
          >
            {{ t('library.downloadZip') }}
          </UiButton>
          <UiMenu :items="menu" :label="t('common.more')" size="lg" />
        </template>
      </CollectionHero>

      <!-- The recording sequence: a strip naming the table, then the ruled
           rows themselves. -->
      <section class="flex flex-col border-b-2 border-line">
        <div
          class="flex h-10 items-stretch gap-3 border-b-2 border-line bg-surface-2 px-3"
        >
          <h2 class="eyebrow flex min-w-0 flex-1 items-center text-fg">
            {{ t('common.tracks', { count: album.tracks.length }) }}
          </h2>
          <span class="mono flex shrink-0 items-center text-faint">{{
            albumLength
          }}</span>
        </div>
        <SelectionBar
          :count="selectedCount"
          :total="total"
          :zipping="zipping"
          @select-all="selectAll"
          @clear="clear"
          @play="playSelected"
          @enqueue="enqueueSelected"
          @zip="zipSelected"
          @delete="deleteSelected"
          @add-to-playlist="addSelectedToPlaylist"
        />
        <TrackList
          v-model:selected="selected"
          :tracks="album.tracks"
          :context="context"
          :show-album="false"
          :show-added="false"
          :show-cover="false"
          :link-artist="false"
          numbering="track"
          :hide-menu="['album']"
        />
      </section>

      <!-- More by the same artist: contiguous square cells, whole cell is
           one link, the play block sits in its own corner. -->
      <section v-if="moreByArtist.length" class="flex flex-col">
        <div
          class="flex h-10 items-stretch gap-3 border-b-2 border-line bg-surface-2 px-3"
        >
          <h2 class="eyebrow flex min-w-0 flex-1 items-center text-fg">
            {{ t('album.moreBy', { artist: album.artist }) }}
          </h2>
          <RouterLink
            :to="{ name: 'Artist', query: { name: album.artist } }"
            class="eyebrow flex shrink-0 items-center text-muted transition-colors duration-100 hover:text-fg"
            >{{ t('common.seeAll') }}</RouterLink
          >
        </div>
        <div
          class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6"
        >
          <article
            v-for="other in moreByArtist"
            :key="other.key"
            class="flex min-w-0 flex-col gap-2 border-r-2 border-b-2 border-line p-2.5 transition-colors duration-100 hover:bg-surface-2"
          >
            <RouterLink
              :to="{
                name: 'Album',
                query: { artist: other.artist, title: other.title },
              }"
              :aria-label="other.title"
              class="block"
            >
              <CoverArt
                :src="other.cover"
                :name="other.title"
                :letter-size="48"
                class="aspect-square w-full"
              />
            </RouterLink>
            <div class="flex items-start gap-2">
              <RouterLink
                :to="{
                  name: 'Album',
                  query: { artist: other.artist, title: other.title },
                }"
                class="min-w-0 flex-1"
              >
                <span class="block truncate text-sm font-semibold">{{
                  other.title
                }}</span>
                <span class="mono mt-0.5 block truncate text-faint">{{
                  other.year
                }}</span>
              </RouterLink>
              <UiIconButton
                icon="play"
                size="sm"
                :label="t('actions.playItem', { name: other.title })"
                @click="actions.play(other.tracks, 0, albumContext(other))"
              />
            </div>
          </article>
        </div>
      </section>
    </DetailState>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import SelectionBar from '/src/components/library/SelectionBar.vue'
import TrackList from '/src/components/library/TrackList.vue'
import { useAuth } from '/src/model/auth'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackActions } from '/src/model/trackActions'
import { useTrackSelection } from '/src/model/selection'
import { albumKey } from '/src/lib/library'
import { formatBytes, splitLength } from '/src/lib/format'
import { useTrashCapability } from '/src/lib/trash'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const auth = useAuth()
const trash = useTrashCapability()

const ready = ref(false)

async function loadAlbum() {
  ready.value = false
  await library.loadArtistTracks(String(route.query.artist || ''))
  ready.value = true
}

onMounted(loadAlbum)
watch(
  () => [route.query.artist, route.query.title],
  () => loadAlbum()
)

const album = computed(() =>
  library.findAlbum(
    String(route.query.artist || ''),
    String(route.query.title || '')
  )
)

function albumContext(item) {
  return {
    type: 'album',
    title: item.title,
    subtitle: item.artist,
    cover: item.cover,
    route: { name: 'Album', query: { artist: item.artist, title: item.title } },
  }
}

const context = computed(() => (album.value ? albumContext(album.value) : null))

const selection = useTrackSelection({
  tracks: () => album.value?.tracks || [],
  resetKey: () => [route.query.artist, route.query.title],
  context: () => context.value,
})
const {
  selected,
  count: selectedCount,
  total,
  zipping,
  selectAll,
  clear,
  playSelected,
  enqueueSelected,
  zipSelected,
  deleteSelected,
  addSelectedToPlaylist,
} = selection

// The mono catalogue line under the title: how long the record is, what it
// was encoded at, and how much disk it takes.
const albumLength = computed(() => {
  const a = album.value
  const { hours, minutes } = splitLength(a.duration)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})

// The mono spec table in the header: what it was encoded at, and what the
// files take on disk.
const albumFormats = computed(() =>
  [...new Set(album.value.tracks.map((track) => track.format))].join(', ')
)

const isThisPlaying = computed(() => {
  const current = player.currentTrack.value
  return (
    player.isPlaying.value &&
    !!current &&
    albumKey(current.albumArtist, current.album) === album.value?.key
  )
})

function togglePlay() {
  if (isThisPlaying.value) player.pause()
  else actions.play(album.value.tracks, 0, context.value)
}

const moreByArtist = computed(() => {
  const artist = library.findArtist(album.value?.artist)
  if (!artist) return []
  return artist.albums
    .filter((other) => other.key !== album.value.key)
    .slice(0, 6)
})

// Admins can put the whole album in one of their playlists (or a new one).
const addToPlaylist = computed(() =>
  playlistActions.addMenuItems(album.value?.tracks || [])
)

const menu = computed(() => [
  {
    label: t('actions.playNext'),
    icon: 'play-next',
    action: () => actions.playNext(album.value.tracks),
  },
  ...(addToPlaylist.value.length
    ? [{ divider: true }, ...addToPlaylist.value, { divider: true }]
    : []),
  {
    label: t('library.downloadZip'),
    icon: 'zip',
    action: () => actions.downloadZip(album.value.tracks),
  },
  {
    label: t('album.searchMore'),
    icon: 'search',
    action: () =>
      router.push({
        name: 'Search',
        params: { query: `${album.value.artist} ${album.value.title}` },
      }),
  },
  { divider: true },
  {
    label: trash.enabled.value ? t('trash.move') : t('album.delete'),
    icon: 'trash',
    danger: true,
    hidden: trash.enabled.value && !auth.isAdmin.value,
    action: async () => {
      const deleted = await actions.remove(album.value.tracks)
      if (deleted.length)
        router.push({ name: 'Library', params: { tab: 'albums' } })
    },
  },
])
</script>
