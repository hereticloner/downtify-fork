<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('stats.title')" />

    <div
      v-if="loading"
      class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6"
    >
      <UiSkeleton v-for="n in 6" :key="n" class="h-20 !rounded-panel" />
    </div>

    <UiEmpty
      v-else-if="error"
      icon="alert"
      :title="t('library.loadFailed')"
      :body="t('library.loadFailedHint')"
    >
      <UiButton icon="refresh" @click="load">{{ t('common.retry') }}</UiButton>
    </UiEmpty>

    <template v-else>
      <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <UiPanel class="p-4">
          <div class="text-3xl font-bold">
            {{ stats.library?.tracks ?? 0 }}
          </div>
          <div class="text-sm text-faint">{{ t('stats.tracks') }}</div>
        </UiPanel>
        <UiPanel class="p-4">
          <div class="text-3xl font-bold">
            {{ stats.library?.playlists ?? 0 }}
          </div>
          <div class="text-sm text-faint">{{ t('stats.playlists') }}</div>
        </UiPanel>
        <UiPanel class="p-4">
          <div class="text-3xl font-bold">
            {{ stats.downloads?.last_30_days ?? 0 }}
          </div>
          <div class="text-sm text-faint">
            {{ t('stats.downloads30') }}
          </div>
        </UiPanel>
        <UiPanel class="p-4">
          <div class="text-3xl font-bold">
            {{ stats.downloads?.total ?? 0 }}
          </div>
          <div class="text-sm text-faint">
            {{ t('stats.downloadsTotal') }}
          </div>
        </UiPanel>
        <UiPanel class="p-4">
          <div class="text-3xl font-bold">
            {{ stats.playback?.total ?? 0 }}
          </div>
          <div class="text-sm text-faint">{{ t('stats.plays') }}</div>
        </UiPanel>
        <UiPanel class="p-4">
          <div class="text-3xl font-bold">{{ stats.library?.likes ?? 0 }}</div>
          <div class="text-sm text-faint">{{ t('stats.likes') }}</div>
        </UiPanel>
      </div>

      <div class="grid items-start gap-6 xl:grid-cols-3">
        <UiPanel class="p-4">
          <h2 class="mb-3 text-lg font-medium">
            {{ t('stats.downloadsPerDay') }}
          </h2>
          <div
            v-if="!(stats.downloads?.per_day || []).length"
            class="text-sm text-faint"
          >
            {{ t('stats.empty') }}
          </div>
          <div
            v-for="d in stats.downloads?.per_day || []"
            :key="d.date"
            class="mb-1 flex items-center gap-2"
          >
            <span class="w-24 shrink-0 text-xs text-faint">{{ d.date }}</span>
            <div class="h-2 flex-1 overflow-hidden rounded bg-line-2">
              <div
                class="h-full bg-accent"
                :style="{
                  width: `${Math.min(100, (d.count / maxDay) * 100)}%`,
                }"
              />
            </div>
            <span class="w-6 text-right text-xs">{{ d.count }}</span>
          </div>
        </UiPanel>

        <UiPanel class="p-4">
          <h2 class="mb-3 text-lg font-medium">{{ t('stats.topTracks') }}</h2>
          <div
            v-if="!(stats.playback?.top_tracks || []).length"
            class="text-sm text-faint"
          >
            {{ t('stats.empty') }}
          </div>
          <ol class="flex flex-col gap-1.5">
            <li
              v-for="(row, i) in stats.playback?.top_tracks || []"
              :key="row.summary"
              class="flex items-baseline gap-2"
            >
              <span class="w-5 text-right text-xs text-faint"
                >{{ i + 1 }}.</span
              >
              <span class="min-w-0 flex-1 truncate text-sm">{{
                row.summary
              }}</span>
              <span class="text-xs text-faint">{{ row.count }}</span>
            </li>
          </ol>
        </UiPanel>

        <UiPanel class="p-4">
          <h2 class="mb-3 text-lg font-medium">
            {{ t('stats.spotifyRecent') }}
          </h2>
          <div
            v-if="!(stats.spotify?.recent || []).length"
            class="text-sm text-faint"
          >
            {{ t('stats.empty') }}
          </div>
          <ol class="flex flex-col gap-1.5">
            <li
              v-for="row in stats.spotify?.recent || []"
              :key="row.played_at"
              class="flex items-baseline gap-2"
            >
              <span class="w-28 shrink-0 text-xs text-faint">{{
                playedAt(row.played_at)
              }}</span>
              <span class="min-w-0 flex-1 truncate text-sm">
                {{ row.artist_name }} - {{ row.track_name }}
              </span>
            </li>
          </ol>
          <div class="mt-3 text-xs text-faint">
            {{
              t('stats.spotifyPlayCount', {
                count: stats.spotify?.play_count ?? 0,
              })
            }}
          </div>
        </UiPanel>
      </div>

      <UiPanel class="p-4">
        <h2 class="mb-3 text-lg font-medium">
          {{ t('stats.activityHeatmap') }}
        </h2>
        <ActivityHeatmap
          :days="stats.playback?.heatmap || []"
          :locale="locale"
          :selected="selectedDay"
          @select="pickDay"
        />
        <div class="mt-4 flex flex-wrap items-center gap-x-8 gap-y-3">
          <div>
            <div class="text-2xl font-bold">{{ streak }}</div>
            <div class="text-xs text-faint">{{ t('stats.streakDays') }}</div>
          </div>
          <div class="flex flex-col gap-1 text-sm">
            <span>{{ t('stats.streak', { count: streak }) }}</span>
            <span v-if="busiest.count" class="text-faint">
              {{
                t('stats.bestDay', {
                  date: busiest.date,
                  count: busiest.count,
                })
              }}
            </span>
            <span v-else class="text-faint">{{ t('stats.empty') }}</span>
          </div>
        </div>
      </UiPanel>

      <!-- What was played, and which queue served it. Picking a day in
           the heatmap above narrows the list to that day. -->
      <div class="grid items-start gap-6 xl:grid-cols-3">
        <UiPanel class="p-4">
          <div class="mb-3 flex items-baseline justify-between gap-3">
            <h2 class="text-lg font-medium">{{ t('stats.recentPlays') }}</h2>
            <button
              v-if="selectedDay"
              type="button"
              class="text-xs text-accent hover:underline"
              @click="pickDay('')"
            >
              {{ t('stats.clearDay') }}
            </button>
          </div>
          <div
            v-if="selectedDay"
            class="mb-2 text-xs text-faint"
            data-day-filter
          >
            {{ t('stats.dayPlays', { date: selectedDay }) }}
          </div>
          <div v-if="!dayPlays.length" class="text-sm text-faint">
            {{ t('stats.empty') }}
          </div>
          <ol class="flex max-h-96 flex-col gap-1.5 overflow-y-auto">
            <li
              v-for="(row, i) in dayPlays"
              :key="`${row.at}-${i}`"
              class="flex items-baseline gap-2"
            >
              <span class="w-14 shrink-0 text-xs text-faint">{{
                clockOf(row.at)
              }}</span>
              <span class="min-w-0 flex-1 truncate text-sm">{{
                row.summary
              }}</span>
              <span
                v-if="row.context"
                class="max-w-32 shrink-0 truncate rounded-full bg-accent/15 px-2 py-0.5 text-xs text-accent"
                :title="t('stats.playedFrom')"
              >
                {{ row.context }}
              </span>
            </li>
          </ol>
        </UiPanel>

        <UiPanel class="p-4">
          <h2 class="mb-3 text-lg font-medium">
            {{ t('stats.topContexts') }}
          </h2>
          <div
            v-if="!(stats.playback?.top_contexts || []).length"
            class="text-sm text-faint"
          >
            {{ t('stats.empty') }}
          </div>
          <ol class="flex flex-col gap-1.5">
            <li
              v-for="(row, i) in stats.playback?.top_contexts || []"
              :key="row.context"
              class="flex items-baseline gap-2"
            >
              <span class="w-5 text-right text-xs text-faint"
                >{{ i + 1 }}.</span
              >
              <span class="min-w-0 flex-1 truncate text-sm">{{
                row.context
              }}</span>
              <span class="text-xs text-faint">{{ row.count }}</span>
            </li>
          </ol>
        </UiPanel>

        <UiPanel class="p-4">
          <h2 class="mb-3 text-lg font-medium">{{ t('stats.trend') }}</h2>
          <div class="text-3xl font-bold">{{ trendTotals.plays }}</div>
          <div class="text-xs text-faint">
            {{ t('stats.trendPlays', { count: trendTotals.plays }) }}
          </div>

          <!-- The last 30 days as a line, scaled to its own busiest day
               so a quiet week still reads as a shape. -->
          <svg
            v-if="trendLine"
            class="mt-3 h-10 w-full text-accent"
            :viewBox="`0 0 ${TREND_W} ${TREND_H}`"
            preserveAspectRatio="none"
            role="img"
            :aria-label="t('stats.trend')"
          >
            <polyline
              :points="trendLine"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              vector-effect="non-scaling-stroke"
            />
          </svg>

          <dl class="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div>
              <dt class="text-faint">{{ t('stats.trendActiveDays') }}</dt>
              <dd class="text-sm font-medium">
                {{
                  t('stats.trendActiveDaysCount', {
                    count: trendTotals.activeDays,
                  })
                }}
              </dd>
            </div>
            <div>
              <dt class="text-faint">{{ t('stats.trendAverage') }}</dt>
              <dd class="text-sm font-medium">{{ trendTotals.average }}</dd>
            </div>
          </dl>
        </UiPanel>
      </div>
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
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import {
  heatmapCells,
  heatmapTotals,
  heatmapTrend,
  trendPoints,
} from '/src/lib/heatmap'
import { useStats } from '/src/model/stats'

const { t, locale } = useI18n()
const { stats, loading, error, load } = useStats()

onMounted(load)

// The trend line is drawn in its own coordinate space and stretched to
// the panel's width, so these are just a stable aspect.
const TREND_W = 100
const TREND_H = 28

const maxDay = computed(() =>
  Math.max(1, ...(stats.value.downloads?.per_day || []).map((d) => d.count))
)

// Days in a row with a play, and the busiest day of the retained
// window - the same two numbers the heatmap panel is built around.
const streak = computed(() => stats.value.playback?.streak_days ?? 0)
const busiest = computed(() => stats.value.playback?.best_day ?? {})

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
// draws, so the line and the cells can never disagree.
const trendCells = computed(() =>
  heatmapTrend(heatmapCells(stats.value.playback?.heatmap || []))
)
const trendTotals = computed(() => heatmapTotals(trendCells.value))
const trendLine = computed(() =>
  trendPoints(trendCells.value, TREND_W, TREND_H)
)

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
