<template>
  <div class="flex flex-col">
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
        <UiButton icon="refresh" @click="load">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="artist" class="animate-rise flex flex-col">
      <CollectionHero
        :title="t('link.topSongsOf', { artist: artist.name })"
        :kicker="kicker"
        :cover="artist.cover_url"
        :name="artist.name"
        icon="user"
        round
      >
        <template #subtitle>
          <span v-if="artist.songs.length" class="tabular">
            {{
              [t('common.tracks', { count: artist.songs.length }), lengthLabel]
                .filter(Boolean)
                .join(' · ')
            }}
          </span>
        </template>
        <template #actions>
          <template v-if="artist.songs.length">
            <UiButton
              v-if="topSongs.newSongs.length"
              variant="primary"
              size="lg"
              icon="download"
              :loading="topSongs.submitting"
              @click="topSongs.download(topSongs.newSongs)"
            >
              {{
                topSongs.newSongs.length === artist.songs.length
                  ? t('link.downloadAll', { count: topSongs.newSongs.length })
                  : t('link.downloadNew', { count: topSongs.newSongs.length })
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
              v-if="
                topSongs.newSongs.length &&
                topSongs.newSongs.length < artist.songs.length
              "
              size="lg"
              @click="topSongs.download(artist.songs)"
            >
              {{ t('link.redownloadAll') }}
            </UiButton>
          </template>
          <UiButton variant="plain" size="lg" icon="arrow-up-right" :href="url">
            <span class="max-sm:sr-only">{{ sourceLabel }}</span>
          </UiButton>
        </template>
      </CollectionHero>

      <div class="grid xl:grid-cols-[minmax(0,1fr)_320px]">
        <div class="flex min-w-0 flex-col">
          <div v-if="artist.songs.length" class="border-b-2 border-line p-3">
            <TopSongsPanel :state="topSongs" />
          </div>
          <div v-else class="border-b-2 border-line p-4">
            <UiEmpty icon="music" :title="t('link.topSongsEmpty')" />
          </div>
        </div>

        <!-- Selection summary: how much of the list is picked, and what it
             holds. -->
        <aside
          v-if="artist.songs.length"
          class="flex min-w-0 flex-col xl:border-l-2 xl:border-line"
        >
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2
              class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
            >
              {{ t('link.downloadSelected') }}
            </h2>
            <span
              class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >{{ topSongs.selected.size }}</span
            >
          </div>
          <dl class="flex flex-col px-3">
            <div
              class="flex items-baseline justify-between gap-3 border-b border-line-2 py-2"
            >
              <dt class="eyebrow">{{ t('library.tracks') }}</dt>
              <dd class="mono tabular text-fg">
                {{ topSongs.selected.size }} / {{ artist.songs.length }}
              </dd>
            </div>
            <div
              v-for="row in summary"
              :key="row.label"
              class="flex items-baseline justify-between gap-3 border-b border-line-2 py-2 last:border-b-0"
            >
              <dt class="eyebrow">{{ row.label }}</dt>
              <dd class="mono tabular text-fg-3">{{ row.value }}</dd>
            </div>
          </dl>
          <p class="mono border-t border-line-2 px-3 py-2 text-faint">
            {{ lengthLabel }}
          </p>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import TopSongsPanel from '/src/components/library/TopSongsPanel.vue'
import API from '/src/model/api'
import { useTopSongs } from '/src/model/topSongs'
import { classifyInput } from '/src/lib/input'
import { splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'

const { t } = useI18n()
const route = useRoute()

const artist = ref(null)
const loading = ref(false)
const error = ref('')
// The list, its selection and its downloads - shared with the artist
// page's Top songs tab (see model/topSongs.js).
const topSongs = useTopSongs(artist)

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))

async function load() {
  if (!url.value) return
  loading.value = true
  error.value = ''
  artist.value = null
  topSongs.reset()
  try {
    const res = await API.artistTopSongs(url.value)
    artist.value = res.data
    topSongs.reset()
  } catch (err) {
    error.value = friendlyError(t, err, 'errors.generic')
  } finally {
    loading.value = false
  }
}

watch(url, load, { immediate: true })

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
  return `${source} · ${t('link.topSongs')}`
})

const lengthLabel = computed(() => {
  const total = (artist.value?.songs || []).reduce(
    (sum, song) => sum + (song.duration || 0),
    0
  )
  if (!total) return ''
  const { hours, minutes } = splitLength(total)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})

// What the list holds, by download state - the same states the rows show.
const summary = computed(() => {
  const rows = topSongs.rows || []
  const count = (status) => rows.filter((row) => row.status === status).length
  return [
    { label: t('link.filterNew'), value: count('new') },
    { label: t('link.filterLibrary'), value: count('library') },
    { label: t('link.filterQueue'), value: count('queue') },
  ]
})
</script>
