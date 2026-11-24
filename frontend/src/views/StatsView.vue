<template>
  <div class="flex flex-col">
    <PageHeader :title="t('stats.title')" class="border-b-2 border-line" />

    <div
      v-if="loading"
      class="grid grid-cols-2 border-l-2 border-line md:grid-cols-3 xl:grid-cols-6"
    >
      <UiSkeleton
        v-for="n in 6"
        :key="n"
        class="h-24 border-r-2 border-b-2 border-line"
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
      <!-- Metric strip: six flush blocks, number first, label under it. -->
      <section
        class="grid grid-cols-2 border-l-2 border-line md:grid-cols-3 xl:grid-cols-6"
      >
        <div
          v-for="(metric, i) in metrics"
          :key="metric.key"
          class="relative border-r-2 border-b-2 border-line px-4 py-3"
        >
          <span
            class="mono absolute top-2 right-2 text-faint"
            aria-hidden="true"
            >{{ String(i + 1).padStart(2, '0') }}</span
          >
          <div
            v-count-up="1500"
            class="text-display stat-reveal tabular text-[34px] leading-none font-bold"
          >
            {{ metric.value }}
          </div>
          <span class="eyebrow mt-2 block truncate">{{ metric.label }}</span>
        </div>
      </section>

      <!-- Ingest chart + top origins: square blocks, mono axes. -->
      <section
        class="grid border-b-2 border-line xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]"
      >
        <div
          class="flex min-w-0 flex-col border-b-2 border-line xl:border-r-2 xl:border-b-0"
        >
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
              {{ t('stats.downloadsPerDay') }}
            </h2>
            <span
              class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >{{ perDay.length }}</span
            >
          </div>
          <div class="min-w-0 flex-1 px-3 py-4">
            <p v-if="!perDay.length" class="text-[13px] text-faint">
              {{ t('stats.empty') }}
            </p>
            <template v-else>
              <div
                role="img"
                :aria-label="t('stats.downloadsPerDay')"
                class="flex h-36 items-end gap-0.5 border-b-2 border-line pb-1"
              >
                <div
                  v-for="day in perDay"
                  :key="day.date"
                  class="flex min-w-0 flex-1 flex-col justify-end gap-0.5"
                  :title="`${day.date}: ${day.count}`"
                >
                  <span
                    v-for="n in CHART_BLOCKS"
                    :key="n"
                    class="h-2 w-full"
                    :class="
                      n <= blockRows(day.count)
                        ? 'bg-fg'
                        : 'border border-line-2'
                    "
                  />
                </div>
              </div>
              <div
                class="mono mt-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-1"
              >
                <span class="text-faint">{{ perDay[0]?.date }}</span>
                <span class="text-faint">{{
                  perDay[perDay.length - 1]?.date
                }}</span>
              </div>
            </template>
          </div>
        </div>

        <div class="flex min-w-0 flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
              {{ t('stats.topContexts') }}
            </h2>
            <span
              class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >{{ topContexts.length }}</span
            >
          </div>
          <div class="min-w-0 flex-1 px-3 py-4">
            <p v-if="!topContexts.length" class="text-[13px] text-faint">
              {{ t('stats.empty') }}
            </p>
            <ul v-else class="flex flex-col">
              <li
                v-for="(row, i) in topContexts"
                :key="row.context"
                class="flex items-center gap-3 border-b border-line-2 py-2 first:pt-0 last:border-b-0 last:pb-0"
              >
                <span class="mono tabular w-5 shrink-0 text-faint">{{
                  String(i + 1).padStart(2, '0')
                }}</span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-[13px]">{{
                    row.context
                  }}</span>
                  <span class="mt-1 flex h-2 gap-0.5" aria-hidden="true">
                    <span
                      v-for="n in BAR_BLOCKS"
                      :key="n"
                      class="min-w-0 flex-1"
                      :class="
                        n <= segmentBlocks(row.count)
                          ? 'bg-fg'
                          : 'border border-line-2'
                      "
                    />
                  </span>
                </span>
                <span class="mono tabular shrink-0 text-muted">{{
                  row.count
                }}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Listening heatmap: one block per day, plus the streak numbers. -->
      <section class="flex flex-col border-b-2 border-line">
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
            {{ t('stats.activityHeatmap') }}
          </h2>
          <span
            class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
            >{{ t('stats.streak', { count: streak }) }}</span
          >
        </div>
        <div class="px-3 py-4">
          <ActivityHeatmap
            :days="stats.playback?.heatmap || []"
            :locale="locale"
            :selected="selectedDay"
            @select="pickDay"
          />
          <div
            class="mt-4 flex flex-col border-2 border-line sm:flex-row sm:items-stretch"
          >
            <div
              class="shrink-0 border-b-2 border-line px-4 py-3 sm:border-r-2 sm:border-b-0"
            >
              <div
                class="text-display tabular text-[30px] leading-none font-bold"
              >
                {{ streak }}
              </div>
              <span class="eyebrow mt-1.5 block">{{
                t('stats.streakDays')
              }}</span>
            </div>
            <div class="flex min-w-0 flex-col justify-center gap-1 px-4 py-3">
              <span class="text-[13px]">{{
                t('stats.streak', { count: streak })
              }}</span>
              <span v-if="busiest.count" class="mono text-faint">
                {{
                  t('stats.bestDay', {
                    date: busiest.date,
                    count: busiest.count,
                  })
                }}
              </span>
              <span v-else class="mono text-faint">{{ t('stats.empty') }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- What was played, from where, and how the last month looked. -->
      <section class="grid border-b-2 border-line xl:grid-cols-3">
        <div
          class="flex min-w-0 flex-col border-b-2 border-line xl:border-r-2 xl:border-b-0"
        >
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
              {{ t('stats.recentPlays') }}
            </h2>
            <button
              v-if="selectedDay"
              type="button"
              class="eyebrow flex shrink-0 items-center border-l-2 border-line px-3 text-muted transition-colors duration-100 hover:text-fg"
              @click="pickDay('')"
            >
              {{ t('stats.clearDay') }}
            </button>
          </div>
          <div class="min-w-0 px-3 py-3">
            <p v-if="selectedDay" class="mono mb-2 text-faint" data-day-filter>
              {{ t('stats.dayPlays', { date: selectedDay }) }}
            </p>
            <p v-if="!dayPlays.length" class="text-[13px] text-faint">
              {{ t('stats.empty') }}
            </p>
            <ol class="flex max-h-96 flex-col overflow-y-auto">
              <li
                v-for="(row, i) in dayPlays"
                :key="`${row.at}-${i}`"
                class="flex items-center gap-2 border-b border-line-2 py-1.5 last:border-b-0"
              >
                <span class="mono tabular w-14 shrink-0 text-faint">{{
                  clockOf(row.at)
                }}</span>
                <span class="min-w-0 flex-1 truncate text-[13px]">{{
                  row.summary
                }}</span>
                <span
                  v-if="row.context"
                  class="mono max-w-32 shrink-0 truncate border border-line-2 px-1.5 text-muted"
                  :title="t('stats.playedFrom')"
                >
                  {{ row.context }}
                </span>
              </li>
            </ol>
          </div>
        </div>

        <div
          class="flex min-w-0 flex-col border-b-2 border-line xl:border-r-2 xl:border-b-0"
        >
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
              {{ t('stats.spotifyRecent') }}
            </h2>
            <span
              class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >{{ stats.spotify?.play_count ?? 0 }}</span
            >
          </div>
          <div class="min-w-0 flex-1 px-3 py-3">
            <p
              v-if="!(stats.spotify?.recent || []).length"
              class="text-[13px] text-faint"
            >
              {{ t('stats.empty') }}
            </p>
            <ol class="flex flex-col">
              <li
                v-for="row in stats.spotify?.recent || []"
                :key="row.played_at"
                class="flex items-baseline gap-3 border-b border-line-2 py-1.5 last:border-b-0"
              >
                <span class="mono tabular shrink-0 text-faint">{{
                  playedAt(row.played_at)
                }}</span>
                <span class="min-w-0 flex-1 truncate text-[13px]">
                  {{ row.artist_name }} - {{ row.track_name }}
                </span>
              </li>
            </ol>
            <p class="mono mt-3 border-t-2 border-line pt-2 text-faint">
              {{
                t('stats.spotifyPlayCount', {
                  count: stats.spotify?.play_count ?? 0,
                })
              }}
            </p>
          </div>
        </div>

        <div class="flex min-w-0 flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
              {{ t('stats.trend') }}
            </h2>
          </div>
          <div class="min-w-0 flex-1 px-3 py-3">
            <div class="flex items-end gap-3">
              <div
                class="text-display tabular text-[30px] leading-none font-bold"
              >
                {{ trendTotals.plays }}
              </div>
              <span class="mono mb-1 text-faint">{{
                t('stats.trendPlays', { count: trendTotals.plays })
              }}</span>
            </div>

            <!-- The last 30 days as square blocks, one column per day,
                 scaled to its own busiest day. -->
            <div
              v-if="trendCells.length"
              class="mt-3 flex h-14 items-end gap-0.5 border-b-2 border-line pb-1"
              role="img"
              :aria-label="t('stats.trend')"
            >
              <div
                v-for="cell in trendCells"
                :key="cell.date"
                class="flex min-w-0 flex-1 flex-col justify-end gap-0.5"
                :title="`${cell.date}: ${cell.count}`"
              >
                <span
                  v-for="n in TREND_BLOCKS"
                  :key="n"
                  class="h-1.5 w-full"
                  :class="
                    n <= trendBlocks(cell.count)
                      ? 'bg-fg'
                      : 'border border-line-2'
                  "
                />
              </div>
            </div>

            <dl class="mt-3 flex flex-col gap-1.5">
              <div class="flex items-baseline justify-between gap-3">
                <dt class="eyebrow">{{ t('stats.trendActiveDays') }}</dt>
                <dd class="mono tabular text-fg-3">
                  {{
                    t('stats.trendActiveDaysCount', {
                      count: trendTotals.activeDays,
                    })
                  }}
                </dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="eyebrow">{{ t('stats.trendAverage') }}</dt>
                <dd class="mono tabular text-fg-3">
                  {{ trendTotals.average }}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from '/src/i18n'
import ActivityHeatmap from '/src/components/library/ActivityHeatmap.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import { heatmapCells, heatmapTotals, heatmapTrend } from '/src/lib/heatmap'
import { useStats } from '/src/model/stats'
// Local registration: SSR renders this view without the app's directives.
import { countUpDirective as vCountUp } from '/src/composables/useCountUp'

const { t, locale } = useI18n()
const { stats, loading, error, load } = useStats()

onMounted(load)

// Block charts: a column of squares per day, 2px apart, never a curve.
const CHART_BLOCKS = 10
const BAR_BLOCKS = 24
const TREND_BLOCKS = 6

const perDay = computed(() => stats.value.downloads?.per_day || [])
const topContexts = computed(() => stats.value.playback?.top_contexts || [])

const maxDay = computed(() =>
  Math.max(1, ...perDay.value.map((day) => Number(day.count) || 0))
)
const maxContext = computed(() =>
  Math.max(1, ...topContexts.value.map((row) => Number(row.count) || 0))
)

/** How many of a column's blocks are filled, 0 for a day with nothing. */
function blockRows(count, max = maxDay.value) {
  const value = Number(count) || 0
  if (!value) return 0
  return Math.max(1, Math.round((value / max) * CHART_BLOCKS))
}

function segmentBlocks(count) {
  const value = Number(count) || 0
  if (!value) return 0
  return Math.max(1, Math.round((value / maxContext.value) * BAR_BLOCKS))
}

// Days in a row with a play, and the busiest day of the retained
// window - the same two numbers the heatmap panel is built around.
const streak = computed(() => stats.value.playback?.streak_days ?? 0)
const busiest = computed(() => stats.value.playback?.best_day ?? {})

// The six numbers the page opens with.
const metrics = computed(() => [
  {
    key: 'tracks',
    label: t('stats.tracks'),
    value: stats.value.library?.tracks ?? 0,
  },
  {
    key: 'playlists',
    label: t('stats.playlists'),
    value: stats.value.library?.playlists ?? 0,
  },
  {
    key: 'downloads30',
    label: t('stats.downloads30'),
    value: stats.value.downloads?.last_30_days ?? 0,
  },
  {
    key: 'downloadsTotal',
    label: t('stats.downloadsTotal'),
    value: stats.value.downloads?.total ?? 0,
  },
  {
    key: 'plays',
    label: t('stats.plays'),
    value: stats.value.playback?.total ?? 0,
  },
  {
    key: 'likes',
    label: t('stats.likes'),
    value: stats.value.library?.likes ?? 0,
  },
])

// The day a heatmap cell was clicked on, or '' for all of them.
const selectedDay = ref('')

/** Clicking the picked day again clears the filter. */
function pickDay(date) {
  selectedDay.value = selectedDay.value === date ? '' : date || ''
}

// Your newest plays, newest first, narrowed to the picked day.
const dayPlays = computed(() => {
  const recent = stats.value.playback?.recent || []
  return selectedDay.value
    ? recent.filter((row) => row.date === selectedDay.value)
    : recent
})

// The trend window: the last 30 days of the same grid the heatmap
// draws, so the blocks and the cells can never disagree.
const trendCells = computed(() =>
  heatmapTrend(heatmapCells(stats.value.playback?.heatmap || []))
)
const trendTotals = computed(() => heatmapTotals(trendCells.value))
const trendMax = computed(() =>
  Math.max(1, ...trendCells.value.map((cell) => Number(cell.count) || 0))
)

function trendBlocks(count) {
  const value = Number(count) || 0
  if (!value) return 0
  return Math.max(1, Math.round((value / trendMax.value) * TREND_BLOCKS))
}

// When a play was made, in the reader's own locale. Activity stamps ISO
// instants; an unparseable one falls back to the raw text rather than
// showing "Invalid Date".
function playedAt(value) {
  const stamp = String(value || '')
  if (!stamp) return ''
  try {
    return new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(stamp))
  } catch {
    return stamp
  }
}

// Just the clock part of an activity stamp, for the per-day list.
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
</script>
