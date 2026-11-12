<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('similar.title')"
      :subtitle="t('similar.subtitle')"
      class="border-b-2 border-line"
    />

    <!-- The seed: what the mix is built from. Enter (like the main search)
         starts it. -->
    <section class="flex flex-col border-b-2 border-line">
      <div class="flex items-stretch border-b-2 border-line bg-surface-2">
        <span
          class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
          >01</span
        >
        <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg">
          {{ t('similar.findSimilar') }}
        </h2>
      </div>
      <form
        class="flex flex-col gap-3 p-4 sm:flex-row sm:items-end sm:px-6"
        @submit.prevent="submit"
      >
        <UiInput
          v-model.trim="artistInput"
          class="sm:flex-1"
          :label="t('similar.artist')"
          :placeholder="t('similar.artistPlaceholder')"
          autocomplete="off"
        />
        <UiInput
          v-model.trim="trackInput"
          class="sm:flex-1"
          :label="t('similar.track')"
          :placeholder="t('similar.trackPlaceholder')"
          autocomplete="off"
        />
      </form>
    </section>

    <div v-if="similar.loading.value" class="border-l-2 border-line">
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
      v-else-if="similar.error.value"
      class="border-b-2 border-line p-4"
      role="status"
    >
      <UiEmpty
        icon="alert"
        :title="t('similar.failed')"
        :body="similar.error.value"
      >
        <UiButton icon="refresh" @click="retry">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div
      v-else-if="similar.searched.value && !similar.songs.value.length"
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="search"
        :title="t('similar.noResults')"
        :body="t('similar.noResultsHint')"
      />
    </div>

    <div
      v-else-if="similar.searched.value"
      class="grid xl:grid-cols-[minmax(0,1fr)_320px]"
    >
      <div class="flex min-w-0 flex-col">
        <section class="flex flex-col border-b-2 border-line">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <span
              class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
              >02</span
            >
            <h2
              class="text-display flex min-w-0 flex-1 items-center px-3 py-2 text-[15px] leading-tight font-bold"
            >
              {{ resultsTitle }}
            </h2>
            <span
              class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >{{ similar.songs.value.length }}</span
            >
          </div>
          <div class="border-2 border-line">
            <TrackDownPlayHeader actions-width="w-40" />
            <div class="divide-y divide-line-2">
              <SimilarTrackRow
                v-for="(song, i) in similar.songs.value"
                :key="`${song.artist}|${song.name}`"
                :song="song"
                :index="i"
                :songs="similar.songs.value"
              />
            </div>
            <!-- The endless list: reaching the end loads the next page. -->
            <div ref="sentinel">
              <div
                v-if="similar.loadingMore.value"
                class="flex h-14 items-center gap-3 border-t border-line-2 px-3"
              >
                <UiSkeleton class="size-9" />
                <div class="flex flex-1 flex-col gap-2">
                  <UiSkeleton class="h-3 w-1/3" />
                  <UiSkeleton class="h-2.5 w-1/5" />
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- The mix as an apparatus reading: what it was seeded with, and how
           much of it has arrived. -->
      <aside class="flex min-w-0 flex-col xl:border-l-2 xl:border-line">
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <h2
            class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
          >
            {{ t('similar.title') }}
          </h2>
        </div>
        <dl class="flex flex-col px-3">
          <div
            class="flex items-baseline justify-between gap-3 border-b border-line-2 py-2"
          >
            <dt class="eyebrow">{{ t('similar.artist') }}</dt>
            <dd class="mono min-w-0 truncate text-fg-3">
              {{ similar.artist.value || '—' }}
            </dd>
          </div>
          <div
            class="flex items-baseline justify-between gap-3 border-b border-line-2 py-2"
          >
            <dt class="eyebrow">{{ t('similar.track') }}</dt>
            <dd class="mono min-w-0 truncate text-fg-3">
              {{ similar.track.value || '—' }}
            </dd>
          </div>
          <div class="flex items-baseline justify-between gap-3 py-2">
            <dt class="eyebrow">{{ t('library.tracks') }}</dt>
            <dd class="mono tabular text-fg">
              {{ similar.songs.value.length }}
            </dd>
          </div>
        </dl>
      </aside>
    </div>

    <div v-else class="grid border-b-2 border-line md:grid-cols-2">
      <div
        v-for="(tip, i) in tips"
        :key="tip.title"
        class="flex flex-col gap-2 border-b-2 border-line p-4 last:border-b-0 md:border-b-0"
        :class="i === 0 ? 'md:border-r-2' : ''"
      >
        <span
          class="flex size-9 items-center justify-center border-2 border-line text-fg"
        >
          <AppIcon :name="tip.icon" :size="16" />
        </span>
        <p class="text-display text-[15px] font-bold">{{ tip.title }}</p>
        <p class="text-[13px] text-pretty text-muted">{{ tip.body }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import TrackDownPlayHeader from '/src/components/library/TrackDownPlayHeader.vue'
import SimilarTrackRow from '/src/components/similar/SimilarTrackRow.vue'
import { useSimilar } from '/src/model/similar'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { songToPlayerTrack } from '/src/model/stream'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const similar = useSimilar()
const library = useLibrary()
const player = usePlayer()

const artistInput = ref(similar.artist.value)
const trackInput = ref(similar.track.value)

watch(
  () => similar.songs.value,
  (songs) => similar.lookupSongs(songs)
)

// A track row's Similar button lands here with ?artist=&track=: fill the
// form and search at once. Guarded by what's already searched, so typing
// in the form (which rewrites the same query below) never re-triggers.
function applyQuery() {
  const artist = String(route.query.artist || '').trim()
  const track = String(route.query.track || '').trim()
  if (!artist && !track) return
  if (artist === similar.artist.value && track === similar.track.value) {
    return
  }
  artistInput.value = artist
  trackInput.value = track
  similar.searchFor(artist, track)
}

watch(() => [route.query.artist, route.query.track], applyQuery, {
  immediate: true,
})

const resultsTitle = computed(() => {
  const a = similar.artist.value
  const seedTrack = similar.track.value
  if (a && seedTrack)
    return t('similar.resultsFor', { track: seedTrack, artist: a })
  if (a) return t('similar.resultsForArtist', { artist: a })
  return t('similar.resultsForTrack', { track: seedTrack })
})

function submit() {
  const artist = artistInput.value.trim()
  const track = trackInput.value.trim()
  if (!artist && !track) return
  // Keep the URL shareable; the watcher above ignores it when it matches
  // what's already searched.
  router.replace({ name: 'Similar', query: { artist, track } })
  similar.searchFor(artist, track)
}

function retry() {
  similar.searchFor(similar.artist.value, similar.track.value)
}

// Scrolling to the list end loads the next page, endlessly.
const sentinel = ref(null)
let observer = null
watch(
  sentinel,
  (el) => {
    observer?.disconnect()
    observer = null
    if (!el || typeof IntersectionObserver === 'undefined') return
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) similar.loadMore()
      },
      { rootMargin: '600px' }
    )
    observer.observe(el)
  },
  { immediate: true }
)
onBeforeUnmount(() => observer?.disconnect())

function isSongCurrent(song, current) {
  if (!current) return false
  const vid = String(song.song_id || '').trim()
  if (vid && String(current.video_id || '').trim() === vid) return true
  const a = String((song.artists || [])[0] || song.artist || '')
    .trim()
    .toLowerCase()
  const n = String(song.name || '')
    .trim()
    .toLowerCase()
  if (!a || !n) return false
  const ca = String(current.artist || (current.artists || [])[0] || '')
    .trim()
    .toLowerCase()
  const cn = String(current.title || current.name || '')
    .trim()
    .toLowerCase()
  return a === ca && n === cn
}

// Playback reached the list tail: grow the list from it and queue what was
// added, so listening never stops at twenty songs.
let extending = false
watch(
  () => player.currentTrack.value,
  async (current) => {
    if (extending || !current || !similar.hasMore.value) return
    const songs = similar.songs.value
    if (!songs.length) return
    if (!isSongCurrent(songs[songs.length - 1], current)) return
    extending = true
    try {
      const added = await similar.loadMore()
      if (added.length) {
        player.enqueue(
          added.map((song) => songToPlayerTrack(song, library.findTrack))
        )
      }
    } finally {
      extending = false
    }
  }
)

const tips = computed(() => [
  {
    icon: 'wand',
    title: t('similar.tipSimilarTitle'),
    body: t('similar.tipSimilarBody'),
  },
  {
    icon: 'download',
    title: t('similar.tipDownloadTitle'),
    body: t('similar.tipDownloadBody'),
  },
])
</script>
