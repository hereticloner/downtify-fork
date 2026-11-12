<template>
  <div class="flex flex-col">
    <PageHeader
      :title="
        artist
          ? t('finder.songsBy', { name: artist.name })
          : t('finder.resultsFor', { query })
      "
      :subtitle="finder.loading.value ? t('search.searching') : ''"
      class="border-b-2 border-line"
    />

    <UiChips v-model="filter" :items="filters" class="px-3 py-0.5" />

    <div v-if="finder.loading.value" class="border-l-2 border-line">
      <div
        v-for="n in 6"
        :key="n"
        class="flex h-14 items-center gap-3 border-b border-line-2 px-3"
      >
        <UiSkeleton class="size-9" />
        <div class="flex flex-1 flex-col gap-2">
          <UiSkeleton class="h-3 w-1/3" />
          <UiSkeleton class="h-2.5 w-1/5" />
        </div>
      </div>
    </div>

    <div
      v-else-if="finder.error.value"
      class="border-b-2 border-line p-4"
      role="status"
    >
      <UiEmpty
        icon="alert"
        :title="t('search.failed')"
        :body="finder.error.value"
      >
        <UiButton icon="refresh" @click="retry">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="!hasResults" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="search"
        :title="t('search.noResults')"
        :body="t('search.noResultsHint')"
      />
    </div>

    <template v-else>
      <!-- Songs -->
      <section
        v-if="show('songs') && finder.songs.value.length"
        class="flex flex-col border-b-2 border-line"
      >
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <span
            class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
            >01</span
          >
          <h2
            class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
          >
            {{ t('search.songs') }}
          </h2>
          <span
            class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
          >
            {{ finder.songs.value.length }}
          </span>
        </div>
        <div class="border-l-2 border-line">
          <TrackDownPlay
            v-for="(song, i) in visibleSongs"
            :key="song.song_id || song.url"
            :song="song"
            :index="i"
            :queue="songQueue"
            :to="browseLocation('song', song)"
          />
        </div>
        <button
          v-if="
            filter === 'all' && finder.songs.value.length > visibleSongs.length
          "
          type="button"
          class="eyebrow flex items-center justify-between gap-3 border-t-2 border-l-2 border-line px-3 py-2 text-muted transition-colors duration-100 hover:bg-surface-2 hover:text-fg"
          @click="filter = 'songs'"
        >
          <span>{{
            t('search.showAllSongs', { count: finder.songs.value.length })
          }}</span>
          <AppIcon name="chevron-right" :size="14" />
        </button>
      </section>

      <!-- Albums -->
      <section
        v-if="show('albums') && finder.albums.value.length"
        class="flex flex-col border-b-2 border-line"
      >
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <span
            class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
            >02</span
          >
          <h2
            class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
          >
            {{ t('search.albums') }}
          </h2>
          <span
            class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
          >
            {{ finder.albums.value.length }}
          </span>
        </div>
        <div
          class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
        >
          <ReleaseCard
            v-for="album in visibleAlbums"
            :key="album.album_id"
            :release="album"
            :to="browseLocation('album', album)"
          />
        </div>
      </section>

      <!-- Artists -->
      <section
        v-if="show('artists') && finder.artists.value.length"
        class="flex flex-col border-b-2 border-line"
      >
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <span
            class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
            >03</span
          >
          <h2
            class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
          >
            {{ t('search.artists') }}
          </h2>
          <span
            class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
          >
            {{ finder.artists.value.length }}
          </span>
        </div>
        <div
          class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
        >
          <ReleaseCard
            v-for="artist in visibleArtists"
            :key="artist.artist_id"
            :release="withPhoto(artist)"
            :to="browseLocation('artist', artist)"
            round
          />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
// What a Finder search found on Deezer - songs, albums and artists, with
// All / Songs / Albums / Artists chips - for `query`, searched as soon as it
// changes; or, given an `artist` ({ id, name }: a Deezer id), that artist's
// songs, all of them listed. A result opens the column view
// (FinderBrowseView).
import { computed, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiChips from '../ui/UiChips.vue'
import UiEmpty from '../ui/UiEmpty.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import PageHeader from '../library/PageHeader.vue'
import TrackDownPlay from '../library/TrackDownPlay.vue'
import ReleaseCard from '../search/ReleaseCard.vue'
import { artistSongsKey, useFinder } from '/src/model/finder'
import { useLibrary } from '/src/model/library'
import { knownArtistPhoto } from '/src/lib/artistPhotoProxy'
import { deezerImage } from '/src/lib/deezerImage'
import { browseLocation } from '/src/lib/finder'
import { playableQueue } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const props = defineProps({
  query: { type: String, default: '' },
  artist: { type: Object, default: null },
})

const { t } = useI18n()
const finder = useFinder()
const library = useLibrary()
const filter = ref('all')

// What is asked for, as model/finder.js keys it.
const key = computed(() =>
  props.artist ? artistSongsKey(props.artist.id) : props.query
)

// The last answer is kept (model/finder.js): coming back to the same
// search shows it again rather than asking Deezer twice.
watch(
  key,
  (value) => {
    // An artist's songs are the whole answer: list them all at once.
    filter.value = props.artist ? 'songs' : 'all'
    if (!value || (value === finder.query.value && !finder.error.value)) {
      return
    }
    if (props.artist) {
      finder.searchArtistSongs(props.artist.id, props.artist.name)
    } else {
      finder.searchFor(value)
    }
  },
  { immediate: true }
)

function retry() {
  if (props.artist) finder.searchArtistSongs(props.artist.id, props.artist.name)
  else finder.searchFor(props.query)
}

// A chip with nothing behind it (an artist's songs have no albums or
// artists) isn't offered.
const filters = computed(() =>
  [
    { id: 'all', label: t('search.all') },
    {
      id: 'songs',
      label: t('search.songs'),
      count: finder.songs.value.length,
    },
    {
      id: 'albums',
      label: t('search.albums'),
      count: finder.albums.value.length,
    },
    {
      id: 'artists',
      label: t('search.artists'),
      count: finder.artists.value.length,
    },
  ].filter((chip) => chip.id === 'all' || chip.count || finder.loading.value)
)

function show(section) {
  return filter.value === 'all' || filter.value === section
}

const hasResults = computed(
  () =>
    finder.songs.value.length ||
    finder.albums.value.length ||
    finder.artists.value.length
)

const visibleSongs = computed(() =>
  filter.value === 'all' ? finder.songs.value.slice(0, 8) : finder.songs.value
)
const visibleAlbums = computed(() =>
  filter.value === 'all' ? finder.albums.value.slice(0, 6) : finder.albums.value
)
const visibleArtists = computed(() =>
  filter.value === 'all'
    ? finder.artists.value.slice(0, 6)
    : finder.artists.value
)

// An artist result shows the photo saved in the library when there is one,
// else its Deezer picture - through the photo proxy, which relays the picture
// it's given instead of searching Deezer for the name.
function withPhoto(artist) {
  const photo = knownArtistPhoto(artist.name, deezerImage(artist.cover_url))
  return { ...artist, cover_url: photo.cover }
}

// Downloaded songs play from the library, in the results' order.
const songQueue = computed(() =>
  playableQueue(finder.songs.value, library.findTrack)
)
</script>
