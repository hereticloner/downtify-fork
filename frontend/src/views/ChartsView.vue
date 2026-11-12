<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('charts.title')"
      :subtitle="t('charts.subtitle')"
      class="border-b-2 border-line"
    />

    <UiTabs v-if="hasData" :items="tabs" :model-value="tab" />

    <div
      v-if="chart.loading.value && !hasData"
      class="flex flex-col"
      aria-busy="true"
    >
      <div class="border-l-2 border-line">
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
        class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
      >
        <div
          v-for="n in 6"
          :key="n"
          class="flex flex-col gap-2 border-r-2 border-b-2 border-line p-2"
        >
          <UiSkeleton class="aspect-square w-full" />
          <UiSkeleton class="h-3 w-3/4" />
          <UiSkeleton class="h-2.5 w-1/2" />
        </div>
      </div>
    </div>

    <div
      v-else-if="chart.error.value && !hasData"
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="alert"
        :title="t('charts.failed')"
        :body="chart.error.value"
      >
        <UiButton icon="refresh" @click="chart.load({ force: true })">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="!hasData" class="border-b-2 border-line p-4">
      <UiEmpty icon="trending" :title="t('charts.empty')" />
    </div>

    <div v-else class="grid xl:grid-cols-[minmax(0,1fr)_320px]">
      <div class="flex min-w-0 flex-col">
        <!-- Region strip: how much of the chart this tab holds. -->
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <span class="mono tabular flex items-center px-3 py-1.5 text-fg-3">
            {{ activeCount }} / {{ totalCount }}
          </span>
          <span
            class="mono ml-auto flex items-center border-l-2 border-line px-3 text-faint"
            >{{ t('charts.title') }}</span
          >
        </div>

        <template v-if="tab === 'tracks'">
          <div
            v-if="!chart.tracks.value.length"
            class="border-b-2 border-line p-4"
          >
            <UiEmpty icon="music" :title="t('charts.empty')" />
          </div>
          <div v-else class="border-b-2 border-line p-3">
            <TrackDownPlayList
              :songs="chart.tracks.value"
              :queue="trackQueue"
              :collection-name="t('charts.title')"
              selectable
              rank-lead
              :toolbar-mode="TOOLBAR_LAZY"
            />
          </div>
        </template>

        <template v-else>
          <div v-if="!activeReleases.length" class="border-b-2 border-line p-4">
            <UiEmpty icon="trending" :title="t('charts.empty')" />
          </div>
          <div
            v-else
            class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-3 2xl:grid-cols-4"
          >
            <ChartTile
              v-for="(item, i) in activeReleases"
              :key="item.album_id || item.artist_id || item.playlist_id"
              :item="item"
              :kind="RELEASE_KIND[tab]"
              :rank="i + 1"
            />
          </div>
        </template>
      </div>

      <!-- The rest of the chart: the other indices, as compact lists. -->
      <aside class="flex min-w-0 flex-col xl:border-l-2 xl:border-line">
        <section v-for="index in indices" :key="index.id" class="flex flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2
              class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
            >
              {{ index.title }}
            </h2>
            <RouterLink
              :to="{ name: 'Charts', params: { tab: index.id } }"
              class="eyebrow flex shrink-0 items-center border-l-2 border-line px-3 text-muted transition-colors duration-100 hover:text-fg"
              >{{ t('common.seeAll') }}</RouterLink
            >
          </div>
          <RouterLink
            v-for="(item, i) in index.items"
            :key="item.album_id || item.artist_id || item.playlist_id"
            :to="{ name: 'Link', query: { url: item.url } }"
            class="flex items-center gap-2 border-b border-line-2 px-3 py-2 transition-colors duration-100 last:border-b-0 hover:bg-surface-2"
          >
            <span class="mono tabular w-5 shrink-0 text-faint">{{
              String(i + 1).padStart(2, '0')
            }}</span>
            <CoverArt
              :src="item.cover_url"
              :name="item.name"
              :icon="index.id === 'artists' ? 'user' : index.icon"
              :letter-size="10"
              class="size-8"
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-[13px] font-semibold">{{
                item.name
              }}</span>
              <span class="mono block truncate text-muted">{{
                index.subtitle(item)
              }}</span>
            </span>
          </RouterLink>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import ChartTile from '/src/components/charts/ChartTile.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import TrackDownPlayList, {
  TOOLBAR_LAZY,
} from '/src/components/library/TrackDownPlayList.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import { useCharts } from '/src/model/charts'
import { useLibrary } from '/src/model/library'
import { playableQueue } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const chart = useCharts()
const library = useLibrary()

const TABS = ['tracks', 'albums', 'artists', 'playlists']
const RELEASE_KIND = {
  albums: 'album',
  artists: 'artist',
  playlists: 'playlist',
}
const lastTab = useLocalStorage('downtify-charts-tab', 'tracks')
const tab = computed(() => {
  const requested = String(route.params.tab || '')
  return TABS.includes(requested) ? requested : lastTab.value
})
watch(tab, (value) => (lastTab.value = value), { immediate: true })
if (!route.params.tab) {
  router.replace({ name: 'Charts', params: { tab: tab.value } })
}

const hasData = computed(
  () =>
    chart.tracks.value.length ||
    chart.albums.value.length ||
    chart.artists.value.length ||
    chart.playlists.value.length
)

const tabs = computed(() => [
  {
    id: 'tracks',
    label: t('library.tracks'),
    count: chart.tracks.value.length,
    to: { name: 'Charts', params: { tab: 'tracks' } },
  },
  {
    id: 'albums',
    label: t('library.albums'),
    count: chart.albums.value.length,
    to: { name: 'Charts', params: { tab: 'albums' } },
  },
  {
    id: 'artists',
    label: t('library.artists'),
    count: chart.artists.value.length,
    to: { name: 'Charts', params: { tab: 'artists' } },
  },
  {
    id: 'playlists',
    label: t('library.playlists'),
    count: chart.playlists.value.length,
    to: { name: 'Charts', params: { tab: 'playlists' } },
  },
])

// The library tracks a chart track's preview/play button queues once it has
// been downloaded - the chart's own order, downloaded songs only.
const trackQueue = computed(() =>
  playableQueue(chart.tracks.value, library.findTrack)
)

const activeReleases = computed(() => {
  if (tab.value === 'albums') return chart.albums.value
  if (tab.value === 'artists') return chart.artists.value
  if (tab.value === 'playlists') return chart.playlists.value
  return []
})

// How much the tab on screen holds, out of the whole chart.
const activeCount = computed(() =>
  tab.value === 'tracks'
    ? chart.tracks.value.length
    : activeReleases.value.length
)
const totalCount = computed(
  () =>
    chart.tracks.value.length +
    chart.albums.value.length +
    chart.artists.value.length +
    chart.playlists.value.length
)

// The three indices beside the table: each the chart of another kind, its
// first five entries.
const indices = computed(() =>
  [
    {
      id: 'albums',
      title: t('library.albums'),
      icon: 'disc',
      items: chart.albums.value.slice(0, 5),
      subtitle: (item) => item.artist || '',
    },
    {
      id: 'artists',
      title: t('library.artists'),
      icon: 'user',
      items: chart.artists.value.slice(0, 5),
      subtitle: (item) => t('search.artist'),
    },
    {
      id: 'playlists',
      title: t('library.playlists'),
      icon: 'playlist',
      items: chart.playlists.value.slice(0, 5),
      subtitle: (item) => item.owner || t('charts.playlist'),
    },
  ].filter((index) => index.items.length)
)

chart.load()
</script>
