<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <h1 class="text-2xl font-semibold">{{ t('stats.title') }}</h1>

    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <UiPanel class="p-4">
        <div class="text-3xl font-bold">{{ stats.library?.tracks ?? 0 }}</div>
        <div class="text-sm text-faint">{{ t('stats.tracks') }}</div>
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
        <div class="text-3xl font-bold">{{ stats.playback?.total ?? 0 }}</div>
        <div class="text-sm text-faint">{{ t('stats.plays') }}</div>
      </UiPanel>
      <UiPanel class="p-4">
        <div class="text-3xl font-bold">{{ stats.library?.likes ?? 0 }}</div>
        <div class="text-sm text-faint">{{ t('stats.likes') }}</div>
      </UiPanel>
    </div>

    <div class="grid items-start gap-6 xl:grid-cols-2">
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
            <span class="w-5 text-right text-xs text-faint">{{ i + 1 }}.</span>
            <span class="min-w-0 flex-1 truncate text-sm">{{
              row.summary
            }}</span>
            <span class="text-xs text-faint">{{ row.count }}</span>
          </li>
        </ol>
      </UiPanel>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from '/src/i18n'
import UiPanel from '/src/components/ui/UiPanel.vue'
import API from '/src/model/api'

const { t } = useI18n()
const stats = ref({})

onMounted(async () => {
  try {
    stats.value = await API.getStats()
  } catch {
    stats.value = {}
  }
})

const maxDay = computed(() =>
  Math.max(1, ...(stats.value.downloads?.per_day || []).map((d) => d.count))
)
</script>
