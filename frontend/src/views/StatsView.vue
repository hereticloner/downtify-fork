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
        <ActivityHeatmap :days="stats.playback?.heatmap || []" />
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
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from '/src/i18n'
import ActivityHeatmap from '/src/components/library/ActivityHeatmap.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import { useStats } from '/src/model/stats'

const { t, locale } = useI18n()
const { stats, loading, error, load } = useStats()

onMounted(load)

const maxDay = computed(() =>
  Math.max(1, ...(stats.value.downloads?.per_day || []).map((d) => d.count))
)

// Days in a row with a play, and the busiest day of the retained
// window - the same two numbers the heatmap panel is built around.
const streak = computed(() => stats.value.playback?.streak_days ?? 0)
const busiest = computed(() => stats.value.playback?.best_day ?? {})

// When a play was made, in the reader's own locale. Spotify stamps
// ISO instants; an unparseable one falls back to the raw text rather
// than showing "Invalid Date".
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
</script>
