<template>
  <div class="flex flex-col">
    <div
      v-if="loading"
      class="grid grid-cols-2 border-l-2 border-line md:grid-cols-4"
    >
      <UiSkeleton
        v-for="n in 4"
        :key="n"
        class="h-28 border-r-2 border-b-2 border-line"
      />
    </div>

    <div v-else-if="error" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="alert"
        :title="t('library.loadFailed')"
        :body="t('library.loadFailedHint')"
      >
        <UiButton icon="refresh" @click="load">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <template v-else>
      <section class="border-b-2 border-line">
        <div class="grid lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div
            class="flex min-w-0 flex-col gap-4 border-b-2 border-line p-4 sm:flex-row sm:items-center sm:p-6 lg:border-r-2 lg:border-b-0"
          >
            <div
              class="flex size-20 shrink-0 items-center justify-center bg-invert font-display text-3xl font-bold text-on-invert sm:size-24"
              aria-hidden="true"
            >
              {{ monogram }}
            </div>
            <div class="min-w-0 flex-1">
              <h1
                class="text-display truncate text-[28px] leading-none font-bold tracking-[-0.02em] sm:text-[32px]"
              >
                {{ username }}
              </h1>
              <p class="eyebrow mt-2">{{ t('stats.profileSubtitle') }}</p>
              <p class="mono mt-2 text-faint">
                {{
                  profile.first_at && profile.last_at
                    ? t('stats.archiveRange', {
                        start: dateLabel(profile.first_at),
                        end: dateLabel(profile.last_at),
                      })
                    : t('stats.profileEmpty')
                }}
              </p>
              <p class="mono mt-1 text-faint">
                {{ t('stats.sourcePriority') }}
              </p>
              <div class="mt-4">
                <UiSegmented
                  v-model="days"
                  :options="periodOptions"
                  show-labels
                />
              </div>
            </div>
          </div>

          <div class="flex min-w-0 flex-col justify-between gap-4 p-4 sm:p-6">
            <div class="flex items-center justify-between gap-3">
              <h2 class="eyebrow">{{ t('stats.topTrack') }}</h2>
              <span class="mono text-faint">#01</span>
            </div>
            <div v-if="topTrack">
              <p class="text-display text-[20px] leading-tight font-bold">
                {{ topTrack.parts.title || topTrack.summary }}
              </p>
              <p class="mt-1 truncate text-[13px] text-muted">
                {{ topTrack.parts.artist }}
                <span v-if="topTrack.parts.album">
                  · {{ topTrack.parts.album }}
                </span>
              </p>
              <p
                class="text-display mt-4 text-[24px] leading-none font-bold tabular"
              >
                {{ number(topTrack.count) }}
                <span class="eyebrow ml-2">{{ t('stats.plays') }}</span>
              </p>
            </div>
            <p v-else class="text-[13px] text-faint">{{ t('stats.empty') }}</p>
          </div>
        </div>
      </section>

      <section
        class="grid grid-cols-2 border-l-2 border-line md:grid-cols-4"
        :aria-label="t('stats.allTime')"
      >
        <div
          v-for="metric in profileMetrics"
          :key="metric.key"
          class="border-r-2 border-b-2 border-line px-4 py-4"
        >
          <div
            v-count-up="1500"
            class="text-display stat-reveal text-[28px] leading-none font-bold tabular"
          >
            {{ metric.value }}
          </div>
          <span class="eyebrow mt-2 block">{{ metric.label }}</span>
        </div>
      </section>

      <section class="border-b-2 border-line p-4 sm:p-6">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="eyebrow">{{ t('stats.allTime') }}</h2>
          <span class="mono text-faint">{{ t('stats.canonicalPlays') }}</span>
        </div>
        <div class="mt-4 flex h-3 border-2 border-line" aria-hidden="true">
          <div
            v-for="row in allSourceRows"
            :key="row.source"
            class="h-full border-r-2 border-line last:border-r-0"
            :class="row.source === 'downtify' ? 'bg-fg' : 'bg-surface-2'"
            :style="{ width: `${sourcePercent(row.count, playbackTotal)}%` }"
          />
        </div>
        <dl class="mt-3 grid gap-2 sm:grid-cols-3">
          <div
            v-for="row in allSourceRows"
            :key="row.source"
            class="flex items-baseline justify-between gap-3 border-b border-line-2 pb-2"
          >
            <dt class="text-[13px]">{{ row.label }}</dt>
            <dd class="mono tabular text-faint">
              {{ number(row.count) }} ({{
                formatPercent(sourcePercent(row.count, playbackTotal) / 100)
              }})
            </dd>
          </div>
        </dl>
      </section>

      <div class="grid xl:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
        <div class="min-w-0 border-b-2 border-line xl:border-r-2 xl:border-b-0">
          <section class="border-b-2 border-line">
            <div class="flex items-stretch border-b-2 border-line bg-surface-2">
              <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
                {{ t('stats.recentPlays') }}
              </h2>
              <span
                data-play-count
                class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
                :title="t('stats.plays')"
              >
                {{ number(playbackTotal) }}
              </span>
            </div>
            <div
              class="overflow-x-auto"
              role="region"
              tabindex="0"
              :aria-label="t('stats.recentPlays')"
            >
              <table class="w-full border-collapse text-left">
                <caption class="sr-only">
                  {{
                    t('stats.recentPlays')
                  }}
                </caption>
                <thead>
                  <tr
                    class="border-b-2 border-line font-technical-data-sm text-technical-data-sm text-primary uppercase"
                  >
                    <th
                      scope="col"
                      class="w-14 border-r-2 border-line px-2 py-2 text-center"
                    >
                      {{ t('stats.initials') }}
                    </th>
                    <th scope="col" class="border-r-2 border-line px-3 py-2">
                      {{ t('stats.track') }}
                    </th>
                    <th scope="col" class="border-r-2 border-line px-3 py-2">
                      {{ t('stats.artist') }}
                    </th>
                    <th scope="col" class="border-r-2 border-line px-3 py-2">
                      {{ t('stats.source') }}
                    </th>
                    <th scope="col" class="px-3 py-2 text-right">
                      {{ t('stats.time') }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, index) in recentRows"
                    :key="`${row.at}-${index}`"
                    class="border-b border-line-2 last:border-b-0"
                  >
                    <td class="border-r-2 border-line p-2">
                      <div
                        class="flex size-8 items-center justify-center border border-line bg-surface-2 font-technical-data-sm text-technical-data-sm"
                      >
                        {{ initials(row.parts.artist || row.parts.title) }}
                      </div>
                    </td>
                    <td
                      class="max-w-72 truncate border-r-2 border-line px-3 py-2 text-[13px]"
                    >
                      {{ row.parts.title || row.summary }}
                    </td>
                    <td
                      class="max-w-44 truncate border-r-2 border-line px-3 py-2 text-[13px] text-muted"
                    >
                      {{ row.parts.artist }}
                    </td>
                    <td class="border-r-2 border-line px-3 py-2">
                      <span
                        v-if="row.source"
                        :data-source="row.source"
                        class="mono inline-block whitespace-nowrap border border-line-2 px-1.5 py-0.5 text-faint"
                      >
                        {{ sourceLabel(row.source) }}
                      </span>
                    </td>
                    <td
                      class="mono whitespace-nowrap px-3 py-2 text-right text-faint"
                    >
                      {{ clockOf(row.at) }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-if="!recentRows.length" class="p-4 text-[13px] text-faint">
                {{ t('stats.empty') }}
              </p>
            </div>
          </section>

          <section class="border-b-2 border-line">
            <div class="flex items-stretch border-b-2 border-line bg-surface-2">
              <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
                {{ t('stats.topArtists') }}
              </h2>
              <span
                class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >
                {{ t('stats.allTime') }}
              </span>
            </div>
            <ol v-if="topArtists.length" class="grid sm:grid-cols-2">
              <li
                v-for="(row, index) in topArtists"
                :key="row.artist"
                class="flex min-w-0 items-baseline gap-3 border-b border-line-2 px-3 py-3 sm:[&:nth-child(odd)]:border-r-2 sm:[&:nth-child(odd)]:border-line"
              >
                <span class="mono w-6 shrink-0 text-faint">{{
                  String(index + 1).padStart(2, '0')
                }}</span>
                <span class="min-w-0 flex-1 truncate font-bold">{{
                  row.artist
                }}</span>
                <span class="mono shrink-0 tabular text-faint">{{
                  number(row.count)
                }}</span>
              </li>
            </ol>
            <p v-else class="p-4 text-[13px] text-faint">
              {{ t('stats.empty') }}
            </p>
          </section>

          <section class="border-b-2 border-line">
            <div class="flex items-stretch border-b-2 border-line bg-surface-2">
              <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
                {{ t('stats.topAlbums') }}
              </h2>
              <span
                class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >
                {{ t('stats.allTime') }}
              </span>
            </div>
            <div
              v-if="topAlbums.length"
              class="grid grid-cols-2 lg:grid-cols-4"
            >
              <article
                v-for="row in topAlbums"
                :key="`${row.artist}-${row.album}`"
                class="min-w-0 border-b-2 border-r-2 border-line p-3 last:border-r-0 lg:[&:nth-child(4n)]:border-r-0"
              >
                <CoverArt
                  :src="row.cover"
                  :name="row.album"
                  :alt="row.album"
                  class="aspect-square [&_.eyebrow]:font-display [&_.eyebrow]:text-[24px] [&_.eyebrow]:font-bold [&_.eyebrow]:text-fg"
                />
                <h3 class="mt-3 truncate font-bold">{{ row.album }}</h3>
                <p class="mt-1 truncate text-[13px] text-muted">
                  {{ row.artist }}
                </p>
                <p class="mono mt-2 text-faint">
                  {{ number(row.count) }} {{ t('stats.plays') }}
                </p>
              </article>
            </div>
            <p v-else class="p-4 text-[13px] text-faint">
              {{ t('stats.empty') }}
            </p>
          </section>

          <section>
            <div class="flex items-stretch border-b-2 border-line bg-surface-2">
              <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
                {{ t('stats.topTracks') }}
              </h2>
              <span
                class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >
                {{ t('stats.allTime') }}
              </span>
            </div>
            <div
              class="overflow-x-auto"
              role="region"
              tabindex="0"
              :aria-label="t('stats.topTracks')"
            >
              <table class="w-full border-collapse text-left">
                <caption class="sr-only">
                  {{
                    t('stats.topTracks')
                  }}
                </caption>
                <thead>
                  <tr
                    class="border-b-2 border-line font-technical-data-sm text-technical-data-sm text-primary uppercase"
                  >
                    <th
                      scope="col"
                      class="w-12 border-r-2 border-line px-2 py-2 text-center"
                    >
                      {{ t('stats.rank') }}
                    </th>
                    <th scope="col" class="border-r-2 border-line px-3 py-2">
                      {{ t('stats.track') }}
                    </th>
                    <th scope="col" class="border-r-2 border-line px-3 py-2">
                      {{ t('stats.artist') }}
                    </th>
                    <th scope="col" class="border-r-2 border-line px-3 py-2">
                      {{ t('stats.album') }}
                    </th>
                    <th scope="col" class="px-3 py-2 text-right">
                      {{ t('stats.plays') }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, index) in topTracks"
                    :key="`${row.artist}-${row.title}-${index}`"
                    class="border-b border-line-2 last:border-b-0"
                  >
                    <td
                      class="mono border-r-2 border-line px-2 py-2 text-center text-faint"
                    >
                      {{ String(index + 1).padStart(2, '0') }}
                    </td>
                    <td
                      class="max-w-64 truncate border-r-2 border-line px-3 py-2 font-bold"
                    >
                      {{ row.parts.title || row.summary }}
                    </td>
                    <td
                      class="max-w-40 truncate border-r-2 border-line px-3 py-2 text-muted"
                    >
                      {{ row.parts.artist }}
                    </td>
                    <td
                      class="max-w-48 truncate border-r-2 border-line px-3 py-2 text-muted"
                    >
                      {{ row.parts.album }}
                    </td>
                    <td
                      class="mono whitespace-nowrap px-3 py-2 text-right tabular"
                    >
                      {{ number(row.count) }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-if="!topTracks.length" class="p-4 text-[13px] text-faint">
                {{ t('stats.empty') }}
              </p>
            </div>
          </section>
        </div>

        <aside class="min-w-0">
          <section class="border-b-2 border-line p-4 sm:p-6">
            <div class="flex items-baseline justify-between gap-3">
              <h2 class="eyebrow">{{ t('stats.listeningReport') }}</h2>
              <span class="mono text-faint">{{
                t('stats.canonicalPlays')
              }}</span>
            </div>
            <ol class="mt-4 flex flex-col gap-4">
              <li v-for="week in weeks" :key="week.start">
                <div class="flex items-baseline justify-between gap-3">
                  <span class="text-[13px]">{{
                    weekLabel(week.start, week.end, locale)
                  }}</span>
                  <span class="mono tabular text-faint">{{
                    number(week.count)
                  }}</span>
                </div>
                <div class="mt-2 h-2 border border-line-2" aria-hidden="true">
                  <div
                    class="h-full bg-fg"
                    :style="{ width: `${weekPercent(week.count)}%` }"
                  />
                </div>
              </li>
            </ol>
          </section>

          <section class="border-b-2 border-line p-4 sm:p-6">
            <h2 class="eyebrow">{{ t('stats.periodSummary', { days }) }}</h2>
            <div
              class="text-display mt-3 text-3xl leading-none font-bold tabular"
            >
              {{ number(period.total ?? 0) }}
              <span class="eyebrow ml-2">{{ t('stats.plays') }}</span>
            </div>
            <dl class="mt-4 flex flex-col gap-2">
              <div
                v-for="row in periodSourceRows"
                :key="row.source"
                class="flex items-baseline justify-between gap-3 border-b border-line-2 pb-2"
              >
                <dt class="text-[13px]">{{ row.label }}</dt>
                <dd class="mono tabular text-faint">
                  {{ number(row.count) }} ({{
                    formatPercent(
                      sourcePercent(row.count, period.total ?? 0) / 100
                    )
                  }})
                </dd>
              </div>
            </dl>
          </section>

          <section class="border-b-2 border-line p-4 sm:p-6">
            <h2 class="eyebrow">{{ t('stats.archiveScope') }}</h2>
            <h3 class="eyebrow mt-4 text-muted">
              {{ t('stats.lastfmDetail') }}
            </h3>
            <dl class="mt-2 flex flex-col gap-2">
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-[13px]">{{ t('stats.lastfmLoved') }}</dt>
                <dd class="mono tabular text-faint">
                  {{ number(lastfm.loved_plays) }}
                </dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-[13px]">{{ t('stats.lastfmMbid') }}</dt>
                <dd class="mono tabular text-faint">
                  {{ number(lastfm.mbid_plays) }}
                </dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-[13px]">
                  {{
                    t('stats.lastfmImported', { count: lastfm.imported_plays })
                  }}
                </dt>
                <dd class="mono tabular text-faint">
                  {{ number(lastfm.imported_plays) }}
                </dd>
              </div>
            </dl>
            <p class="mono mt-3 border-t-2 border-line pt-2 text-faint">
              {{ lastfmImportLabel }}
            </p>
          </section>

          <section class="p-4 sm:p-6">
            <h2 class="eyebrow">{{ t('stats.knownTrackTime') }}</h2>
            <div
              class="text-display mt-3 text-[24px] leading-none font-bold tabular"
            >
              {{ t('stats.hoursMinutes', trackTimeParts) }}
            </div>
            <p class="mono mt-2 text-faint">{{ t('stats.trackTimeHint') }}</p>
            <p class="mono mt-1 text-faint">
              {{
                t('stats.durationCoverage', {
                  with: trackTime.plays_with_duration,
                  total: period.total ?? 0,
                })
              }}
            </p>
          </section>
        </aside>
      </div>

      <footer class="border-t-2 border-line px-4 py-4 sm:px-6">
        <p class="mono text-faint">{{ t('stats.historyCoverage') }}</p>
        <p class="mono mt-1 text-faint">{{ t('stats.trackTimeHint') }}</p>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useI18n } from '/src/i18n'
import { useAuth } from '/src/model/auth'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import { countUpDirective as vCountUp } from '/src/composables/useCountUp'
import { formatPercent, initials, splitLength } from '/src/lib/format'
import { albumKey } from '/src/lib/library'
import { trackParts, weekLabel } from '/src/lib/statsProfile'
import { useLibrary } from '/src/model/library'
import { useStats } from '/src/model/stats'

const { t, locale } = useI18n()
const auth = useAuth()
const library = useLibrary()
const { stats, loading, error, days, load } = useStats()

onMounted(() => {
  load()
  // Artwork is optional decoration: a failed background lookup must not
  // break the profile.
  if (!library.albumsComplete.value) {
    void library.ensureAlbums().catch(() => {})
  }
})
watch(days, () => load())

const coverByAlbum = computed(() => {
  const map = new Map()
  for (const album of library.albums.value || []) {
    if (!album.cover) continue
    const key = albumKey(album.artist, album.title)
    if (!map.has(key)) map.set(key, album.cover)
  }
  return map
})

const periodOptions = computed(() => [
  { value: 7, label: t('stats.period7') },
  { value: 30, label: t('stats.period30') },
  { value: 90, label: t('stats.period90') },
])

const playback = computed(() => stats.value.playback || {})
const playbackTotal = computed(() => Number(playback.value.total) || 0)
const profile = computed(
  () =>
    playback.value.profile || {
      first_at: '',
      last_at: '',
      unique: { tracks: 0, artists: 0, albums: 0 },
      by_source: { downtify: 0, spotify: 0, lastfm: 0 },
      top_artists: [],
      top_albums: [],
      weeks: [],
    }
)
const period = computed(
  () => playback.value.period || { total: 0, by_source: {} }
)
const trackTime = computed(
  () =>
    playback.value.track_time || {
      seconds: 0,
      plays_with_duration: 0,
      plays_without_duration: 0,
    }
)
const lastfm = computed(
  () =>
    playback.value.lastfm || {
      loved_plays: 0,
      mbid_plays: 0,
      imported_plays: 0,
      backfill: {},
    }
)

const username = computed(() => auth.user.value?.username || '')
const monogram = computed(() => initials(username.value) || '—')
const profileMetrics = computed(() => [
  {
    key: 'plays',
    label: t('stats.totalPlays'),
    value: number(playbackTotal.value),
  },
  {
    key: 'artists',
    label: t('stats.uniqueArtists'),
    value: number(profile.value.unique.artists),
  },
  {
    key: 'tracks',
    label: t('stats.uniqueTracks'),
    value: number(profile.value.unique.tracks),
  },
  {
    key: 'albums',
    label: t('stats.knownAlbums'),
    value: number(profile.value.unique.albums),
  },
])

const topTracks = computed(() =>
  (playback.value.top_tracks || []).map((row) => ({
    ...row,
    parts: trackParts(row),
  }))
)
const topTrack = computed(() => topTracks.value[0] || null)
const topArtists = computed(() => profile.value.top_artists || [])
const topAlbums = computed(() =>
  (profile.value.top_albums || []).map((row) => ({
    ...row,
    cover: coverByAlbum.value.get(albumKey(row.artist, row.album)) || '',
  }))
)
const recentRows = computed(() =>
  (playback.value.recent || [])
    .filter((row) => row.source !== 'spotify')
    .slice(0, 10)
    .map((row) => ({
      ...row,
      parts: trackParts(row),
    }))
)
const weeks = computed(() => profile.value.weeks || [])
const weekMax = computed(() =>
  Math.max(1, ...weeks.value.map((week) => Number(week.count) || 0))
)

const SOURCE_LABELS = {
  downtify: 'stats.sourceDowntify',
  spotify: 'stats.sourceSpotify',
  lastfm: 'stats.sourceLastfm',
}

function sourceLabel(source) {
  return t(SOURCE_LABELS[source] || SOURCE_LABELS.downtify)
}

function sourceRows(bySource) {
  return ['downtify', 'lastfm'].map((source) => ({
    source,
    label: sourceLabel(source),
    count: Number(bySource?.[source]) || 0,
  }))
}

const allSourceRows = computed(() => sourceRows(profile.value.by_source))
const periodSourceRows = computed(() => sourceRows(period.value.by_source))

function sourcePercent(count, total) {
  const denominator = Number(total) || 0
  return denominator > 0 ? ((Number(count) || 0) / denominator) * 100 : 0
}

function weekPercent(count) {
  return ((Number(count) || 0) / weekMax.value) * 100
}

function number(value) {
  return new Intl.NumberFormat(locale.value).format(Number(value) || 0)
}

function dateLabel(value) {
  const stamp = String(value || '')
  if (!stamp) return ''
  try {
    return new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'medium',
      timeZone: 'UTC',
    }).format(new Date(stamp))
  } catch {
    return stamp
  }
}

function clockOf(value) {
  const stamp = String(value || '')
  if (!stamp) return ''
  try {
    return new Intl.DateTimeFormat(locale.value, {
      timeStyle: 'short',
    }).format(new Date(stamp))
  } catch {
    return stamp.slice(11, 16)
  }
}

const trackTimeParts = computed(() => splitLength(trackTime.value.seconds))

const lastfmImportLabel = computed(() => {
  if (!Number(lastfm.value.imported_plays)) return t('stats.lastfmImportNone')
  if (lastfm.value.backfill?.done) return t('stats.lastfmImportDone')
  return t('stats.lastfmImporting', {
    date: dateLabel(lastfm.value.backfill?.oldest_at),
  })
})
</script>
