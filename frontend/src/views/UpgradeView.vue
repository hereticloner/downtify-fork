<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('upgrade.title')"
      :subtitle="t('upgrade.subtitle')"
      class="border-b-2 border-line"
    >
      <UiButton variant="secondary" icon="library" :to="{ name: 'Library' }">
        {{ t('library.backToLibrary') }}
      </UiButton>
      <UiButton v-if="canPause" variant="secondary" icon="pause" @click="pause">
        {{ t('upgrade.pause') }}
      </UiButton>
      <UiButton v-if="canResume" variant="primary" icon="play" @click="resume">
        {{ t('upgrade.resume') }}
      </UiButton>
      <UiButton v-if="canCancel" variant="danger" icon="x" @click="cancel">
        {{ t('upgrade.cancel') }}
      </UiButton>
      <UiButton
        v-if="canScan"
        variant="primary"
        icon="refresh"
        :loading="loading"
        @click="runScan"
      >
        {{ hasRun ? t('upgrade.rescan') : t('upgrade.scan') }}
      </UiButton>
    </PageHeader>

    <p
      v-if="error"
      role="alert"
      class="border-b-2 border-line bg-surface-2 px-4 py-2 text-[13px] text-danger"
    >
      {{ error }}
    </p>

    <!-- Scanning: one block, a 24-cell matrix, the count under it. -->
    <section v-if="isScanning" class="flex flex-col border-b-2 border-line">
      <div class="flex items-stretch border-b-2 border-line bg-surface-2">
        <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
          {{ t('upgrade.scanning') }}
        </h2>
        <span
          class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-fg-3"
          >{{ scan.pct }}%</span
        >
      </div>
      <div class="px-4 py-4">
        <UiProgress
          :value="scan.pct"
          :indeterminate="!scan.total"
          :height="12"
        />
        <p class="mono mt-2 text-muted">
          {{
            t('upgrade.scanProgress', {
              done: scan.scanned,
              total: scan.total,
            })
          }}
        </p>
      </div>
    </section>

    <!-- Running / paused / finished -->
    <section v-else-if="hasQueue" class="flex flex-col border-b-2 border-line">
      <div class="flex items-stretch border-b-2 border-line bg-surface-2">
        <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
          {{ isRunning ? t('upgrade.working') : stateTitle }}
        </h2>
        <span
          class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-fg-3"
          >{{ tracks.pct }}%</span
        >
      </div>
      <div class="px-4 py-4">
        <UiProgress :value="tracks.pct" :height="12" />
        <div class="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1">
          <span class="mono tabular text-fg">
            {{
              t('upgrade.ofTracks', { done: tracks.done, total: tracks.total })
            }}
          </span>
          <span v-if="bytes.total" class="mono tabular text-muted">
            {{
              t('upgrade.ofBytes', {
                done: formatBytes(bytes.done),
                total: formatBytes(bytes.total),
              })
            }}
          </span>
          <span class="mono tabular text-faint">{{ tracks.pct }}%</span>
        </div>
        <dl class="mt-4 grid grid-cols-2 gap-x-6 sm:grid-cols-4">
          <div
            v-for="item in tallies"
            :key="item.key"
            class="flex items-baseline justify-between gap-3 border-b border-line-2 py-1"
          >
            <dt class="eyebrow truncate">{{ item.label }}</dt>
            <dd class="mono tabular text-fg">{{ item.value }}</dd>
          </div>
        </dl>
        <p
          v-if="isRunning"
          class="mt-4 flex items-start gap-2 text-[13px] text-pretty text-muted"
        >
          <AppIcon name="info" :size="15" class="mt-0.5 shrink-0" />
          {{ t('upgrade.longJob') }}
        </p>
      </div>
    </section>

    <!-- Scan finished, waiting for the user to choose -->
    <template v-if="waitingToStart">
      <section class="flex flex-col border-b-2 border-line">
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
            {{ t('upgrade.scanResult') }}
          </h2>
          <span
            class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
            >{{ t('upgrade.librarySize') }} ·
            {{ formatBytes(summary.libraryBytes) }}</span
          >
        </div>
        <div class="px-4 py-3">
          <p class="mono text-muted">
            {{ t('upgrade.libraryCount', { count: summary.libraryTracks }) }}
          </p>
          <div class="mt-3 flex flex-col border-2 border-line">
            <div
              v-for="name in found"
              :key="name"
              class="flex items-center gap-3 border-b border-line-2 px-3 py-3 last:border-b-0"
            >
              <UiSwitch
                :model-value="selected.includes(name)"
                :label="t(`upgrade.${name}`)"
                :description="t(`upgrade.${name}Hint`)"
                class="min-w-0 flex-1"
                @update:model-value="(on) => toggle(name, on)"
              />
              <UiBadge tone="accent" class="shrink-0">
                {{
                  t('upgrade.tracksAffected', {
                    count: summary.categories[name] || 0,
                  })
                }}
              </UiBadge>
            </div>
          </div>
        </div>
      </section>

      <section class="flex flex-col border-b-2 border-line">
        <div class="flex items-stretch border-b-2 border-line bg-surface-2">
          <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
            {{ t('upgrade.options') }}
          </h2>
        </div>
        <div class="flex flex-col px-4">
          <div
            class="flex flex-wrap items-center justify-between gap-3 border-b border-line-2 py-3"
          >
            <span class="min-w-0 flex-1">
              <span class="block text-[13px] font-semibold text-fg">
                {{ t('upgrade.artworkMin') }}
              </span>
              <span class="mono mt-0.5 block text-muted">
                {{ t('upgrade.artworkMinHint') }}
              </span>
            </span>
            <UiSelect
              v-model="artworkMin"
              :options="sizeOptions"
              :label="t('upgrade.artworkMin')"
              icon="disc"
            />
          </div>
          <div
            class="flex flex-wrap items-center justify-between gap-3 border-b border-line-2 py-3"
          >
            <span class="min-w-0 flex-1 text-[13px] font-semibold text-fg">
              {{ t('upgrade.artworkSource') }}
            </span>
            <UiSelect
              v-model="artworkSource"
              :options="sourceOptions"
              :label="t('upgrade.artworkSource')"
              icon="palette"
            />
          </div>
          <div
            class="flex flex-wrap items-center justify-between gap-3 border-b border-line-2 py-3"
          >
            <span class="min-w-0 flex-1">
              <span class="block text-[13px] font-semibold text-fg">
                {{ t('upgrade.recheck') }}
              </span>
              <span class="mono mt-0.5 block text-muted">
                {{ t('upgrade.recheckHint') }}
              </span>
            </span>
            <UiSelect
              v-model="recheckDays"
              :options="recheckOptions"
              :label="t('upgrade.recheck')"
              icon="clock"
            />
          </div>
        </div>
      </section>

      <div class="flex flex-col gap-3 border-b-2 border-line px-4 py-3">
        <p class="flex items-start gap-2 text-[13px] text-pretty text-muted">
          <AppIcon name="lock" :size="15" class="mt-0.5 shrink-0" />
          {{ t('upgrade.safeNote') }}
        </p>
        <p class="flex items-start gap-2 text-[13px] text-pretty text-muted">
          <AppIcon name="info" :size="15" class="mt-0.5 shrink-0" />
          {{ t('upgrade.audioNote') }}
        </p>
        <div
          class="flex flex-wrap items-center gap-3 border-t-2 border-line pt-3"
        >
          <UiButton
            variant="primary"
            size="lg"
            icon="wand"
            :disabled="!selected.length"
            @click="start"
          >
            {{ t('upgrade.startCount', { count: willRun }) }}
          </UiButton>
          <p v-if="!selected.length" class="mono text-muted">
            {{ t('upgrade.pickSomething') }}
          </p>
        </div>
      </div>
    </template>

    <!-- Nothing to do -->
    <div v-else-if="state === 'ready'" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="check"
        :title="t('upgrade.nothingTitle')"
        :body="
          summary.recentlyChecked
            ? t('upgrade.nothingCheckedBody', {
                count: summary.recentlyChecked,
              })
            : t('upgrade.nothingBody')
        "
      >
        <UiButton
          v-if="summary.recentlyChecked"
          variant="secondary"
          icon="refresh"
          :loading="loading"
          @click="rescanEverything"
        >
          {{ t('upgrade.recheckNever') }}
        </UiButton>
      </UiEmpty>
    </div>

    <!-- Never scanned -->
    <div v-else-if="!busy && !hasQueue" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="sparkle"
        :title="t('upgrade.notScannedTitle')"
        :body="t('upgrade.notScannedBody')"
      >
        <UiButton
          variant="primary"
          icon="refresh"
          :loading="loading"
          @click="runScan"
        >
          {{ t('upgrade.scan') }}
        </UiButton>
      </UiEmpty>
    </div>

    <!-- Per-track rows: 56px rows, a status chip per file. -->
    <section v-if="jobs.length" class="flex flex-col border-b-2 border-line">
      <div class="flex items-stretch border-b-2 border-line bg-surface-2">
        <h2 class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2">
          {{ t('upgrade.tracksTitle') }}
        </h2>
        <span
          class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
          >{{ jobs.length }}</span
        >
      </div>
      <ul class="flex flex-col">
        <li
          v-for="job in jobs"
          :key="job.file"
          class="flex min-h-14 flex-wrap items-center gap-x-3 gap-y-1 border-b border-line-2 px-4 py-2 last:border-b-0"
        >
          <span class="min-w-0 flex-1">
            <span class="block truncate text-[13px] font-semibold text-fg">
              {{ job.title || job.file }}
            </span>
            <span class="mono block truncate text-muted">
              {{ job.artist }}
            </span>
          </span>
          <span v-if="job.detail" class="mono text-muted">
            {{ job.detail }}
          </span>
          <UiBadge :tone="toneFor(job)" :icon="iconFor(job)">
            {{ labelFor(job) }}
          </UiBadge>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import AppIcon from '/src/components/ui/AppIcon.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import { formatBytes } from '/src/lib/format'
import { ARTWORK_SIZES } from '/src/lib/upgrade'
import { useUpgrade } from '/src/model/upgrade'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const {
  status,
  state,
  counts,
  summary,
  jobs,
  tracks,
  bytes,
  scan,
  found,
  busy,
  selected,
  willRun,
  loading,
  error,
  load,
  startScan,
  start,
  pause,
  resume,
  cancel,
  toggle,
  isScanning,
  isRunning,
  waitingToStart,
  canScan,
  canPause,
  canResume,
  canCancel,
} = useUpgrade()

const artworkMin = ref(600)
const artworkSource = ref('highest')
const recheckDays = ref(30)

const runScan = () =>
  startScan({
    artwork_min_px: artworkMin.value,
    artwork_source: artworkSource.value,
    recheck_days: recheckDays.value,
  })

// "Nothing to upgrade" when everything was simply checked recently is a
// dead end without a way past the memory.
function rescanEverything() {
  recheckDays.value = 0
  return runScan()
}

onMounted(() => load())

// Show the values the last scan actually ran with, so re-running it
// from another device doesn't silently use different ones.
watch(
  () => status.value.options,
  (options) => {
    if (!options) return
    if (options.artwork_min_px) artworkMin.value = options.artwork_min_px
    if (options.artwork_source) artworkSource.value = options.artwork_source
    if (typeof options.recheck_days === 'number') {
      recheckDays.value = options.recheck_days
    }
  },
  { immediate: true }
)

const hasRun = computed(() => state.value !== 'idle')
const hasQueue = computed(
  () =>
    counts.value.total > 0 &&
    ['running', 'paused', 'done', 'cancelled'].includes(state.value)
)

const stateTitle = computed(
  () =>
    ({
      paused: t('upgrade.paused'),
      done: t('upgrade.done'),
      cancelled: t('upgrade.cancelled'),
    })[state.value] || t('upgrade.working')
)

const tallies = computed(() =>
  [
    { key: 'completed', value: counts.value.completed },
    { key: 'skipped', value: counts.value.skipped },
    { key: 'failed', value: counts.value.failed },
    { key: 'queued', value: counts.value.queued },
  ].map((item) => ({ ...item, label: t(`upgrade.${item.key}`) }))
)

const sizeOptions = computed(() =>
  ARTWORK_SIZES.map((px) => ({ value: px, label: `${px}px` }))
)

const sourceOptions = computed(() => [
  { value: 'highest', label: t('upgrade.highest') },
  { value: 'spotify', label: t('upgrade.preferSpotify') },
  { value: 'itunes', label: t('upgrade.preferItunes') },
  { value: 'youtube-music', label: t('upgrade.preferYoutube') },
])

const recheckOptions = computed(() => [
  { value: 0, label: t('upgrade.recheckNever') },
  ...[7, 30, 90, 365].map((days) => ({
    value: days,
    label: t('upgrade.recheckDays', { count: days }),
  })),
])

const JOB_TONES = {
  done: 'accent',
  failed: 'danger',
  running: 'warn',
  queued: 'neutral',
  skipped: 'neutral',
}
const JOB_ICONS = {
  done: 'check',
  failed: 'alert',
  running: 'refresh',
  queued: 'clock',
  skipped: 'minus',
}
const STAGE_KEYS = {
  matching: 'upgrade.stageMatching',
  artwork: 'upgrade.stageArtwork',
  lyrics: 'upgrade.stageLyrics',
  writing: 'upgrade.stageWriting',
}

const toneFor = (job) => JOB_TONES[job.status] || 'neutral'
const iconFor = (job) => JOB_ICONS[job.status] || ''

function labelFor(job) {
  if (job.status === 'running' && STAGE_KEYS[job.stage]) {
    return t(STAGE_KEYS[job.stage])
  }
  return t(`upgrade.${job.status === 'done' ? 'completed' : job.status}`)
}
</script>
