<template>
  <div class="flex flex-col">
    <PageHeader :title="t('stats.title')" class="border-b-2 border-line">
      <UiSegmented v-model="days" :options="periodOptions" show-labels />
    </PageHeader>

    <div
      v-if="loading"
      class="grid grid-cols-2 border-l-2 border-line md:grid-cols-3 xl:grid-cols-8"
    >
      <UiSkeleton
        v-for="n in 8"
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
        class="grid grid-cols-2 border-l-2 border-line md:grid-cols-4 xl:grid-cols-8"
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

      <!-- Selected-period listening profile, sourced only from canonical plays. -->
      <section class="border-b-2 border-line">
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
            {{ t('stats.listeningProfile') }}
          </h2>
          <span
            class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
            >{{ days }}</span
          >
        </div>
        <div class="grid grid-cols-2 border-l-2 border-line md:grid-cols-4">
          <div
            v-for="metric in profileMetrics"
            :key="metric.key"
            class="border-r-2 border-b-2 border-line px-4 py-3"
          >
            <div
              class="text-display tabular text-[28px] leading-none font-bold"
            >
              {{ metric.value }}
            </div>
            <span class="eyebrow mt-2 block truncate">{{ metric.label }}</span>
          </div>
        </div>
        <div class="grid xl:grid-cols-3">
          <div
            class="flex min-w-0 flex-col border-b-2 border-line px-3 py-4 xl:border-r-2 xl:border-b-0"
          >
            <h3 class="eyebrow mb-3">{{ t('stats.sourceSplit') }}</h3>
            <ul class="flex flex-col gap-3">
              <li v-for="row in sourceRows" :key="row.source">
                <div class="mb-1 flex items-baseline justify-between gap-3">
                  <span class="text-[13px]">{{ row.label }}</span>
                  <span class="mono tabular text-faint">{{ row.count }}</span>
                </div>
                <div class="h-2 border border-line-2" aria-hidden="true">
                  <div
                    class="h-full bg-fg"
                    :style="{ width: `${sourcePercent(row.count)}%` }"
                  />
                </div>
              </li>
            </ul>
          </div>
          <div
            class="flex min-w-0 flex-col border-b-2 border-line px-3 py-4 xl:border-r-2 xl:border-b-0"
          >
            <h3 class="eyebrow">{{ t('stats.knownTrackTime') }}</h3>
            <div
              class="text-display mt-2 tabular text-[28px] leading-none font-bold"
            >
              {{ formatDuration(trackTime.seconds) }}
            </div>
            <p class="mono mt-2 text-faint">{{ t('stats.trackTimeHint') }}</p>
            <p class="mono mt-1 text-faint">
              {{
                t('stats.durationCoverage', {
                  with: trackTime.plays_with_duration,
                  total: profilePeriod.total ?? 0,
                })
              }}
            </p>
          </div>
          <div class="flex min-w-0 flex-col px-3 py-4">
            <h3 class="eyebrow mb-3">{{ t('stats.lastfmDetail') }}</h3>
            <dl class="flex flex-col gap-2">
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-[13px]">{{ t('stats.lastfmLoved') }}</dt>
                <dd class="mono tabular text-fg-3">{{ lastfm.loved_plays }}</dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-[13px]">{{ t('stats.lastfmMbid') }}</dt>
                <dd class="mono tabular text-fg-3">{{ lastfm.mbid_plays }}</dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-[13px]">
                  {{
                    t('stats.lastfmImported', { count: lastfm.imported_plays })
                  }}
                </dt>
                <dd class="mono tabular text-fg-3">
                  {{ lastfm.imported_plays }}
                </dd>
              </div>
            </dl>
            <p class="mono mt-3 border-t-2 border-line pt-2 text-faint">
              {{ lastfmImportLabel }}
            </p>
          </div>
        </div>
        <p class="mono border-t-2 border-line px-3 py-2 text-faint">
          {{ t('stats.historyCoverage') }}
        </p>
      </section>

      <!-- UTC patterns: real buttons with exact bucket drilldown. -->
      <section class="border-b-2 border-line">
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
            {{ t('stats.patterns') }}
          </h2>
        </div>
        <ListeningPatterns
          :hours="stats.playback?.patterns?.by_hour || []"
          :weekdays="stats.playback?.patterns?.by_weekday || []"
          :selected="selectedPattern"
          :period-total="profilePeriod.total ?? 0"
          :locale="locale"
          @select="pickPattern"
        />
        <div v-if="selectedPattern" class="border-t-2 border-line">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h3 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
              {{ t('stats.patternDetail') }} · {{ patternTitle }}
            </h3>
            <span
              class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >{{ patternDetail.total }}</span
            >
            <button
              type="button"
              class="eyebrow flex shrink-0 items-center border-l-2 border-line px-3 text-muted transition-colors duration-100 hover:text-fg"
              @click="clearPattern"
            >
              {{ t('stats.patternClear') }}
            </button>
          </div>
          <div class="px-3 py-4" :aria-busy="patternLoading">
            <template v-if="patternLoading">
              <UiSkeleton class="mb-2 h-8" />
              <UiSkeleton class="mb-2 h-8" />
              <UiSkeleton class="h-8" />
            </template>
            <div
              v-else-if="patternError"
              class="flex flex-col items-start gap-2"
            >
              <p class="text-[13px] text-faint">
                {{ t('stats.patternLoadFailed') }}
              </p>
              <UiButton icon="refresh" @click="retryPattern">{{
                t('common.retry')
              }}</UiButton>
            </div>
            <p v-else-if="!patternDetail.total" class="text-[13px] text-faint">
              {{ t('stats.patternEmpty') }}
            </p>
            <template v-else>
              <div class="mb-4 flex flex-wrap gap-2">
                <span
                  v-for="row in patternSourceRows"
                  :key="row.source"
                  class="mono border border-line-2 px-2 py-1 text-faint"
                  >{{ row.label }} {{ row.count }}</span
                >
              </div>
              <div class="grid gap-4 xl:grid-cols-3">
                <div>
                  <h4 class="eyebrow mb-2">
                    {{ t('stats.patternTopTracks') }}
                  </h4>
                  <ol class="flex flex-col gap-1.5">
                    <li
                      v-for="row in patternDetail.top_tracks"
                      :key="row.summary"
                      class="flex items-baseline justify-between gap-3 text-[13px]"
                    >
                      <span class="min-w-0 flex-1 truncate">{{
                        row.summary
                      }}</span>
                      <span class="mono tabular text-faint">{{
                        row.count
                      }}</span>
                    </li>
                  </ol>
                </div>
                <div>
                  <h4 class="eyebrow mb-2">
                    {{ t('stats.patternTopArtists') }}
                  </h4>
                  <ol class="flex flex-col gap-1.5">
                    <li
                      v-for="row in patternDetail.top_artists"
                      :key="row.artist"
                      class="flex items-baseline justify-between gap-3 text-[13px]"
                    >
                      <span class="min-w-0 flex-1 truncate">{{
                        row.artist
                      }}</span>
                      <span class="mono tabular text-faint">{{
                        row.count
                      }}</span>
                    </li>
                  </ol>
                </div>
                <div class="min-w-0">
                  <h4 class="eyebrow mb-2">{{ t('stats.patternRecent') }}</h4>
                  <ol
                    class="flex max-h-72 flex-col overflow-y-auto"
                    role="list"
                  >
                    <li
                      v-for="(row, index) in patternDetail.recent"
                      :key="`${row.at}-${index}`"
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
                        >{{ contextName(row.context) }}</span
                      >
                      <span
                        v-if="row.source"
                        class="mono shrink-0 whitespace-nowrap border border-line-2 px-1.5 text-faint"
                        >{{ sourceLabel(row.source) }}</span
                      >
                    </li>
                  </ol>
                </div>
              </div>
              <p
                v-if="patternDetail.truncated"
                class="mono mt-3 border-t-2 border-line pt-2 text-faint"
              >
                {{
                  t('stats.patternTruncated', {
                    shown: patternDetail.recent.length,
                    total: patternDetail.total,
                  })
                }}
              </p>
            </template>
          </div>
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
                    contextName(row.context)
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
            <span
              data-play-count
              class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              :title="t('stats.plays')"
            >
              {{ stats.playback?.total ?? 0 }}
            </span>
            <button
              v-if="selectedDay"
              type="button"
              class="eyebrow flex shrink-0 items-center border-l-2 border-line px-3 text-muted transition-colors duration-100 hover:text-fg"
              @click="pickDay('')"
            >
              {{ t('stats.clearDay') }}
            </button>
          </div>
          <div class="min-w-0 px-3 py-3" :aria-busy="selectedDay && dayLoading">
            <p v-if="selectedDay" class="mono mb-2 text-faint" data-day-filter>
              {{ t('stats.dayPlays', { date: selectedDay }) }} · {{ dayTotal }}
            </p>
            <template v-if="selectedDay && dayLoading">
              <UiSkeleton class="mb-2 h-7" />
              <UiSkeleton class="mb-2 h-7" />
              <UiSkeleton class="h-7" />
            </template>
            <div
              v-else-if="selectedDay && dayError"
              class="flex flex-col items-start gap-2"
            >
              <p class="text-[13px] text-faint">
                {{ t('stats.dayLoadFailed') }}
              </p>
              <UiButton icon="refresh" @click="retryDay">{{
                t('common.retry')
              }}</UiButton>
            </div>
            <p v-else-if="!dayPlays.length" class="text-[13px] text-faint">
              {{ t('stats.empty') }}
            </p>
            <ol class="flex max-h-96 flex-col overflow-y-auto" role="list">
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
                  {{ contextName(row.context) }}
                </span>
                <span
                  v-if="row.source"
                  :data-source="row.source"
                  class="mono shrink-0 whitespace-nowrap border border-line-2 px-1.5 text-faint"
                >
                  {{ sourceLabel(row.source) }}
                </span>
              </li>
            </ol>
            <p
              v-if="selectedDay && dayTotal > dayPlays.length"
              class="mono mt-2 border-t-2 border-line pt-2 text-faint"
            >
              {{
                t('stats.dayTruncated', {
                  shown: dayPlays.length,
                  total: dayTotal,
                })
              }}
            </p>
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
            <ol class="flex flex-col" role="list">
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
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from '/src/i18n'
import { contextLabel } from '/src/lib/context'
import ActivityHeatmap from '/src/components/library/ActivityHeatmap.vue'
import ListeningPatterns from '/src/components/library/ListeningPatterns.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import { formatDuration, formatPercent } from '/src/lib/format'
import { heatmapCells, heatmapTotals, heatmapTrend } from '/src/lib/heatmap'
import { playsForDay, useStats } from '/src/model/stats'
// Local registration: SSR renders this view without the app's directives.
import { countUpDirective as vCountUp } from '/src/composables/useCountUp'

const { t, locale } = useI18n()
const {
  stats,
  loading,
  error,
  dayLoading,
  dayError,
  patternLoading,
  patternError,
  selectedPattern,
  days,
  load,
  loadPattern,
  clearPattern,
} = useStats()

onMounted(() => load())
watch(days, () => load(selectedDay.value))

// Block charts: a column of squares per day, 2px apart, never a curve.
const CHART_BLOCKS = 10
const BAR_BLOCKS = 24
const TREND_BLOCKS = 6

const periodOptions = computed(() => [
  { value: 7, label: t('stats.period7') },
  { value: 30, label: t('stats.period30') },
  { value: 90, label: t('stats.period90') },
])

const perDay = computed(() => stats.value.downloads?.per_day || [])
const topContexts = computed(() => stats.value.playback?.top_contexts || [])
const contextLabels = computed(() => stats.value.playback?.context_labels || {})

function contextName(value) {
  return contextLabel(value, contextLabels.value, t)
}

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

// The eight numbers the page opens with.
const measured = computed(() => stats.value.playback?.measured || {})
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
    key: 'listeningTime',
    label: t('stats.measuredListening'),
    value: formatDuration(measured.value.seconds),
  },
  {
    key: 'completed',
    label: `${t('stats.completed')} · ${formatPercent(
      measured.value.completion_rate
    )}`,
    value: measured.value.completions ?? 0,
  },
  {
    key: 'skipped',
    label: `${t('stats.skipped')} · ${formatPercent(measured.value.skip_rate)}`,
    value: measured.value.skips ?? 0,
  },
  {
    key: 'likes',
    label: t('stats.likes'),
    value: stats.value.library?.likes ?? 0,
  },
])

const profilePeriod = computed(() => stats.value.playback?.period || {})
const profileUnique = computed(() => stats.value.playback?.unique || {})
const trackTime = computed(
  () =>
    stats.value.playback?.track_time || {
      seconds: 0,
      plays_with_duration: 0,
      plays_without_duration: 0,
    }
)
const lastfm = computed(
  () =>
    stats.value.playback?.lastfm || {
      loved_plays: 0,
      mbid_plays: 0,
      imported_plays: 0,
      backfill: {},
    }
)
const profileMetrics = computed(() => [
  {
    key: 'periodPlays',
    label: t('stats.periodPlays'),
    value: profilePeriod.value.total ?? 0,
  },
  {
    key: 'uniqueTracks',
    label: t('stats.uniqueTracks'),
    value: profileUnique.value.tracks ?? 0,
  },
  {
    key: 'uniqueArtists',
    label: t('stats.uniqueArtists'),
    value: profileUnique.value.artists ?? 0,
  },
  {
    key: 'knownAlbums',
    label: t('stats.knownAlbums'),
    value: profileUnique.value.albums ?? 0,
  },
])

// The day a heatmap cell was clicked on, or '' for all of them.
const selectedDay = ref('')
let skipDayLoad = false

/** Clicking the picked day again clears the filter and any pattern drilldown. */
function pickDay(date) {
  const next = selectedDay.value === date ? '' : date || ''
  if (next) clearPattern()
  selectedDay.value = next
}

function pickPattern(selection) {
  if (selectedDay.value) {
    skipDayLoad = true
    selectedDay.value = ''
  }
  loadPattern(selection.kind, selection.bucket)
}

function retryPattern() {
  if (selectedPattern.value) {
    loadPattern(selectedPattern.value.kind, selectedPattern.value.bucket)
  }
}

// Selected-day rows come from the exact-day endpoint, not the recent page.
const dayPlays = computed(() => playsForDay(stats.value, selectedDay.value))
const dayTotal = computed(() =>
  selectedDay.value && stats.value.playback?.day?.date === selectedDay.value
    ? (stats.value.playback.day.total ?? 0)
    : 0
)
watch(selectedDay, (date) => {
  if (skipDayLoad) {
    skipDayLoad = false
    return
  }
  load(date, { background: true })
})

function retryDay() {
  load(selectedDay.value, { background: true })
}

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

const SOURCE_LABELS = {
  downtify: 'stats.sourceDowntify',
  spotify: 'stats.sourceSpotify',
  lastfm: 'stats.sourceLastfm',
}

function sourceLabel(source) {
  return t(SOURCE_LABELS[source] || SOURCE_LABELS.downtify)
}

const sourceRows = computed(() =>
  ['downtify', 'spotify', 'lastfm'].map((source) => ({
    source,
    label: sourceLabel(source),
    count: Number(profilePeriod.value.by_source?.[source]) || 0,
  }))
)
const sourceMax = computed(() =>
  Math.max(1, ...sourceRows.value.map((row) => row.count))
)

function sourcePercent(count) {
  return ((Number(count) || 0) / sourceMax.value) * 100
}

const lastfmImportLabel = computed(() => {
  if (!Number(lastfm.value.imported_plays)) return t('stats.lastfmImportNone')
  if (lastfm.value.backfill?.done) return t('stats.lastfmImportDone')
  return t('stats.lastfmImporting', {
    date: playedAt(lastfm.value.backfill?.oldest_at),
  })
})

const patternDetail = computed(
  () =>
    stats.value.playback?.pattern_detail || {
      kind: '',
      bucket: null,
      total: 0,
      by_source: {},
      top_tracks: [],
      top_artists: [],
      recent: [],
      truncated: false,
    }
)
const patternSourceRows = computed(() =>
  ['downtify', 'spotify', 'lastfm'].map((source) => ({
    source,
    label: sourceLabel(source),
    count: Number(patternDetail.value.by_source?.[source]) || 0,
  }))
)

function patternWeekdayFull(weekday) {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      weekday: 'long',
      timeZone: 'UTC',
    }).format(new Date(Date.UTC(2024, 0, 7 + Number(weekday))))
  } catch {
    return String(weekday)
  }
}

const patternTitle = computed(() => {
  const selected = selectedPattern.value
  if (!selected) return ''
  if (selected.kind === 'weekday') return patternWeekdayFull(selected.bucket)
  return t('stats.patternHourTitle', {
    hour: String(selected.bucket).padStart(2, '0'),
  })
})

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
