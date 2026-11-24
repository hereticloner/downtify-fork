<template>
  <div class="flex flex-col">
    <template v-if="!query">
      <PageHeader
        :title="t('search.title')"
        :subtitle="t('search.subtitle')"
        class="border-b-2 border-line"
      />

      <!-- Three entry blocks, flush -->
      <div class="grid border-b-2 border-line md:grid-cols-3">
        <div
          v-for="tip in tips"
          :key="tip.title"
          class="flex flex-col gap-2 border-b-2 border-line p-4 md:border-r-2 md:border-b-0 md:last:border-r-0"
        >
          <span
            class="flex size-9 items-center justify-center border-2 border-line text-fg"
          >
            <AppIcon :name="tip.icon" :size="17" />
          </span>
          <p class="text-display text-[15px] font-bold">{{ tip.title }}</p>
          <p class="text-[13px] text-pretty text-muted">{{ tip.body }}</p>
        </div>
      </div>

      <section v-if="recent.length" class="flex flex-col">
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <span
            class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
            >#</span
          >
          <h2
            class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
          >
            {{ t('search.recent') }}
          </h2>
          <button
            type="button"
            class="eyebrow flex items-center border-l-2 border-line px-3 text-muted transition-colors duration-100 hover:text-fg"
            @click="recent = []"
          >
            {{ t('common.clear') }}
          </button>
        </div>
        <div class="flex flex-wrap gap-1 p-3">
          <RouterLink
            v-for="term in recent"
            :key="term"
            :to="{ name: 'Search', params: { query: term } }"
            class="mono flex h-8 items-center gap-2 border border-line-2 px-2.5 text-fg-3 transition-colors duration-100 hover:border-line hover:bg-surface-2"
          >
            <AppIcon name="clock" :size="13" class="text-faint" />{{ term }}
          </RouterLink>
        </div>
      </section>
    </template>

    <template v-else>
      <PageHeader
        :title="t('search.resultsFor', { query })"
        :subtitle="search.loading.value ? t('search.searching') : ''"
        class="border-b-2 border-line"
      />

      <!-- Filter strip: one block per index section, the chosen one inverts. -->
      <div
        class="flex items-stretch overflow-x-auto border-b-2 border-line [scrollbar-width:none]"
      >
        <button
          v-for="entry in filters"
          :key="entry.id"
          type="button"
          class="eyebrow flex h-9 shrink-0 items-center gap-2 border-r border-line-2 px-3 whitespace-nowrap transition-colors duration-100"
          :class="
            entry.id === filter
              ? 'bg-invert text-on-invert'
              : 'text-muted hover:bg-surface-2 hover:text-fg'
          "
          :aria-pressed="entry.id === filter"
          @click="filter = entry.id"
        >
          {{ entry.label }}
          <span v-if="entry.count !== undefined" class="mono">{{
            entry.count
          }}</span>
        </button>
        <span class="mono ml-auto flex shrink-0 items-center px-3 text-faint">{{
          resultCount
        }}</span>
      </div>

      <div v-if="search.loading.value" class="border-l-2 border-line">
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
        v-else-if="search.error.value && !search.songs.value.length"
        class="border-b-2 border-line p-4"
      >
        <UiEmpty
          icon="alert"
          :title="t('search.failed')"
          :body="search.error.value"
        >
          <UiButton icon="refresh" @click="search.searchFor(query)">{{
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

      <div v-else class="grid xl:grid-cols-[minmax(0,1fr)_300px]">
        <div class="flex min-w-0 flex-col">
          <!-- Local library -->
          <section
            v-if="show('library') && search.localTracks.value.length"
            class="flex flex-col border-b-2 border-line"
          >
            <div class="flex items-stretch border-b-2 border-line bg-surface-2">
              <span
                class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
                >00</span
              >
              <h2
                class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
              >
                {{ t('search.library') }}
              </h2>
              <span
                class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >
                {{ search.localTracks.value.length }}
              </span>
            </div>
            <TrackList
              :tracks="search.localTracks.value"
              :header="false"
              :show-added="false"
              :context="{ type: 'search', title: search.query.value }"
            />
          </section>

          <!-- Tracks -->
          <section
            v-if="show('songs') && search.songs.value.length"
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
                {{ search.songs.value.length }}
              </span>
            </div>
            <div class="border-l-2 border-line">
              <SongRow
                v-for="(song, i) in visibleSongs"
                :key="song.song_id || song.url"
                :song="song"
                :index="i"
              />
            </div>
            <button
              v-if="
                filter === 'all' &&
                search.songs.value.length > visibleSongs.length
              "
              type="button"
              class="eyebrow flex items-center justify-between gap-3 border-t-2 border-l-2 border-line px-3 py-2 text-muted transition-colors duration-100 hover:bg-surface-2 hover:text-fg"
              @click="filter = 'songs'"
            >
              <span>{{
                t('search.showAllSongs', { count: search.songs.value.length })
              }}</span>
              <AppIcon name="chevron-right" :size="14" />
            </button>
          </section>

          <!-- Albums -->
          <section
            v-if="show('albums') && search.albums.value.length"
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
                {{ search.albums.value.length }}
              </span>
            </div>
            <div
              class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 lg:grid-cols-4"
            >
              <ReleaseCard
                v-for="album in visibleAlbums"
                :key="album.album_id || album.url"
                :release="album"
              />
            </div>
          </section>

          <!-- Artists -->
          <section
            v-if="show('artists') && search.artists.value.length"
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
                {{ search.artists.value.length }}
              </span>
            </div>
            <div
              class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 lg:grid-cols-4"
            >
              <ReleaseCard
                v-for="artist in visibleArtists"
                :key="artist.artist_id || artist.url"
                :release="artist"
                round
              />
            </div>
          </section>
        </div>

        <!-- Apparatus: the search buffer -->
        <aside
          class="flex min-w-0 flex-col xl:-ml-0.5 xl:border-l-2 xl:border-line"
        >
          <UiPanel
            v-if="recent.length"
            :title="t('search.recent')"
            class="-mt-0.5 first:mt-0"
          >
            <template #actions>
              <UiButton variant="ghost" size="sm" @click="recent = []">
                {{ t('common.clear') }}
              </UiButton>
            </template>
            <ul class="mono flex flex-col">
              <li
                v-for="term in recent"
                :key="term"
                class="border-b border-line-2 last:border-b-0"
              >
                <RouterLink
                  :to="{ name: 'Search', params: { query: term } }"
                  class="flex h-9 items-center gap-2 text-muted transition-colors duration-100 hover:text-fg"
                >
                  <AppIcon
                    name="clock"
                    :size="13"
                    class="shrink-0 text-faint"
                  />
                  <span class="truncate">{{ term }}</span>
                </RouterLink>
              </li>
            </ul>
          </UiPanel>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import TrackList from '/src/components/library/TrackList.vue'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import SongRow from '/src/components/search/SongRow.vue'
import { useSearch } from '/src/model/search'
import { useLibrary } from '/src/model/library'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const search = useSearch()
const library = useLibrary()
const filter = ref('all')
const recent = useLocalStorage('downtify-recent-searches', [])

watch(
  () => search.songs.value,
  (songs) => library.lookupSongs(songs)
)

const query = computed(() => String(route.params.query || '').trim())

watch(
  query,
  (value) => {
    filter.value = 'all'
    if (!value) return
    recent.value = [
      value,
      ...recent.value.filter((term) => term !== value),
    ].slice(0, 10)
    if (value !== search.query.value || !search.songs.value.length) {
      search.searchFor(value)
    }
  },
  { immediate: true }
)

const filters = computed(() => [
  { id: 'all', label: t('search.all') },
  {
    id: 'library',
    label: t('search.library'),
    count: search.localTracks.value.length,
  },
  { id: 'songs', label: t('search.songs'), count: search.songs.value.length },
  {
    id: 'albums',
    label: t('search.albums'),
    count: search.albums.value.length,
  },
  {
    id: 'artists',
    label: t('search.artists'),
    count: search.artists.value.length,
  },
])

function show(section) {
  return filter.value === 'all' || filter.value === section
}

const hasResults = computed(
  () =>
    search.localTracks.value.length ||
    search.songs.value.length ||
    search.albums.value.length ||
    search.artists.value.length
)

const resultCount = computed(
  () =>
    search.localTracks.value.length +
    search.songs.value.length +
    search.albums.value.length +
    search.artists.value.length
)

const visibleSongs = computed(() =>
  filter.value === 'all' ? search.songs.value.slice(0, 8) : search.songs.value
)
const visibleAlbums = computed(() =>
  filter.value === 'all' ? search.albums.value.slice(0, 6) : search.albums.value
)
const visibleArtists = computed(() =>
  filter.value === 'all'
    ? search.artists.value.slice(0, 6)
    : search.artists.value
)

const tips = computed(() => [
  {
    icon: 'search',
    title: t('search.tipSearchTitle'),
    body: t('search.tipSearchBody'),
  },
  {
    icon: 'spotify',
    title: t('search.tipSpotifyTitle'),
    body: t('search.tipSpotifyBody'),
  },
  {
    icon: 'youtube',
    title: t('search.tipYoutubeTitle'),
    body: t('search.tipYoutubeBody'),
  },
])
</script>
