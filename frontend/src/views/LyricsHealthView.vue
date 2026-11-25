<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('lyricsHealth.title')"
      :subtitle="t('lyricsHealth.subtitle')"
      class="border-b-2 border-line"
    >
      <UiButton
        v-if="auth.isAdmin.value && eligibleFiles.length"
        variant="primary"
        icon="download"
        :loading="filling"
        @click="fill"
      >
        {{ t('lyricsHealth.fill') }}
      </UiButton>
      <UiButton
        v-if="auth.isAdmin.value"
        variant="secondary"
        icon="refresh"
        :loading="loading"
        @click="load"
      >
        {{ t('lyricsHealth.scan') }}
      </UiButton>
    </PageHeader>

    <div v-if="!auth.isAdmin.value" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="lock"
        :title="t('lyricsHealth.adminOnly')"
        :body="t('lyricsHealth.adminOnlyHint')"
      />
    </div>

    <div
      v-else-if="loading"
      class="border-b-2 border-line p-4"
      aria-busy="true"
    >
      <span class="sr-only">{{ t('lyricsHealth.loading') }}</span>
      <UiSkeleton class="h-24" />
    </div>

    <div v-else-if="error" role="alert" class="border-b-2 border-line p-4">
      <UiEmpty icon="alert" :title="error">
        <UiButton icon="refresh" @click="load">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <template v-else-if="report">
      <section
        class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3"
        :aria-label="t('lyricsHealth.summary')"
      >
        <div
          v-for="status in LYRICS_STATUSES"
          :key="status"
          class="border-r-2 border-b-2 border-line px-4 py-3"
        >
          <div class="mono tabular text-[28px] leading-none font-bold">
            {{ counts[status] }}
          </div>
          <div class="eyebrow mt-2 text-muted">
            {{ t('lyricsHealth.statuses.' + status) }}
          </div>
        </div>
      </section>

      <div class="border-b-2 border-line px-3 py-1">
        <UiChips
          :items="statusItems"
          v-model="status"
          :aria-label="t('lyricsHealth.filter')"
        />
      </div>

      <div
        class="mono flex flex-wrap items-center gap-x-4 border-b border-line-2 px-4 py-2 text-faint"
      >
        <span>{{
          t('lyricsHealth.scannedAt', { date: formattedScannedAt })
        }}</span>
        <span v-if="report.warnings?.length" class="text-danger">
          {{ t('lyricsHealth.partial') }}
        </span>
        <span v-if="filling" class="text-accent">{{ progress }}</span>
      </div>

      <p
        v-if="fillResult"
        role="status"
        class="border-b border-line-2 px-4 py-2 text-[13px] text-muted"
      >
        {{
          t('lyricsHealth.fillResult', {
            written: fillResult.written,
            skipped: fillResult.skipped,
            failed: fillResult.failed,
          })
        }}
      </p>
      <ul
        v-if="fillErrors.length"
        class="border-b border-line-2 px-4 py-2 text-[13px] text-danger"
      >
        <li v-for="item in fillErrors" :key="`${item.file}:${item.code}`">
          <span class="mono">{{ item.file }}</span>
          — {{ t('lyricsHealth.errors.' + item.code) }}
        </li>
      </ul>
      <p
        v-if="fillError"
        role="alert"
        class="border-b border-line-2 px-4 py-2 text-[13px] text-danger"
      >
        {{ fillError }}
      </p>

      <div v-if="!visibleFindings.length" class="border-b-2 border-line p-4">
        <UiEmpty
          icon="check"
          :title="t('lyricsHealth.empty')"
          :body="t('lyricsHealth.emptyHint')"
        />
      </div>

      <div
        v-else
        role="region"
        tabindex="0"
        :aria-label="t('lyricsHealth.findings')"
        class="lyrics-table-wrap border-b-2 border-line"
      >
        <table class="lyrics-table">
          <caption class="sr-only">
            {{
              t('lyricsHealth.findings')
            }}
          </caption>
          <thead>
            <tr>
              <th scope="col">{{ t('track.title') }}</th>
              <th scope="col">{{ t('track.artist') }}</th>
              <th scope="col">{{ t('track.album') }}</th>
              <th scope="col">{{ t('lyricsHealth.status') }}</th>
              <th scope="col">{{ t('lyricsHealth.file') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="finding in visibleFindings" :key="finding.file">
              <th scope="row" :data-label="t('track.title')">
                {{ finding.title || '—' }}
              </th>
              <td :data-label="t('track.artist')">
                {{ finding.artist || '—' }}
              </td>
              <td :data-label="t('track.album')">
                {{ finding.album || '—' }}
              </td>
              <td :data-label="t('lyricsHealth.status')">
                {{ t('lyricsHealth.statuses.' + finding.status) }}
              </td>
              <td :data-label="t('lyricsHealth.file')">
                <span class="mono block truncate" :title="finding.file">{{
                  finding.file
                }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="px-4 py-3 text-[13px] text-pretty text-muted">
        {{ t('lyricsHealth.readOnly') }}
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import PageHeader from '/src/components/library/PageHeader.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import { useI18n } from '/src/i18n'
import { useAuth } from '/src/model/auth'
import {
  LYRICS_STATUSES,
  chunkFiles,
  eligibleLyricsFiles,
  lyricsStatusCounts,
} from '/src/lib/lyricsHealth'
import { fillLyricsHealth, scanLyricsHealth } from '/src/model/lyricsHealth'

const { t, locale } = useI18n()
const auth = useAuth()
const report = ref(null)
const loading = ref(auth.isAdmin.value)
const filling = ref(false)
const error = ref('')
const fillError = ref('')
const fillResult = ref(null)
const fillErrors = ref([])
const progress = ref('')
const status = ref('all')

const counts = computed(() => lyricsStatusCounts(report.value))
const eligibleFiles = computed(() =>
  eligibleLyricsFiles(report.value, report.value?.synced_only)
)
const visibleFindings = computed(() => {
  const rows = report.value?.findings || []
  return status.value === 'all'
    ? rows
    : rows.filter((finding) => finding.status === status.value)
})
const statusItems = computed(() => [
  {
    id: 'all',
    label: t('lyricsHealth.statuses.all'),
    count: report.value?.summary?.tracks || 0,
  },
  ...LYRICS_STATUSES.map((key) => ({
    id: key,
    label: t('lyricsHealth.statuses.' + key),
    count: counts.value[key],
  })),
])
const formattedScannedAt = computed(() => {
  if (!report.value?.scanned_at) return ''
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(report.value.scanned_at))
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    report.value = await scanLyricsHealth()
  } catch {
    error.value = t('lyricsHealth.loadFailed')
  } finally {
    loading.value = false
  }
}

async function fill() {
  filling.value = true
  fillError.value = ''
  fillErrors.value = []
  fillResult.value = { written: 0, skipped: 0, failed: 0 }
  const batches = chunkFiles(eligibleFiles.value)
  try {
    for (const [index, files] of batches.entries()) {
      progress.value = t('lyricsHealth.progress', {
        current: index + 1,
        total: batches.length,
      })
      const result = await fillLyricsHealth(files)
      for (const key of ['written', 'skipped', 'failed']) {
        fillResult.value[key] += Number(result[key] || 0)
      }
      fillErrors.value.push(...(result.errors || []))
    }
    await load()
  } catch {
    fillError.value = t('lyricsHealth.fillFailed')
  } finally {
    filling.value = false
    progress.value = ''
  }
}

onMounted(() => {
  if (auth.isAdmin.value) void load()
})
</script>

<style scoped>
.lyrics-table-wrap {
  container-type: inline-size;
  overflow: auto;
  max-block-size: min(70vh, 720px);
}

.lyrics-table {
  min-inline-size: 900px;
  border-collapse: separate;
  border-spacing: 0;
}

.lyrics-table th,
.lyrics-table td {
  border-bottom: 1px solid var(--color-line-2);
  padding: 10px 12px;
  text-align: start;
  vertical-align: top;
}

.lyrics-table thead th {
  position: sticky;
  inset-block-start: 0;
  z-index: 1;
  border-bottom-width: 2px;
  background: var(--color-surface-2);
  color: var(--color-muted);
  font-family: var(--font-label);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.lyrics-table tbody tr:hover {
  background: var(--color-surface-2);
}

@container (width < 600px) {
  .lyrics-table {
    min-inline-size: 0;
  }

  .lyrics-table thead {
    display: none;
  }

  .lyrics-table,
  .lyrics-table tbody,
  .lyrics-table tr,
  .lyrics-table th,
  .lyrics-table td {
    display: block;
  }

  .lyrics-table tbody tr {
    border-bottom: 2px solid var(--color-line);
    padding-block: 8px;
  }

  .lyrics-table th,
  .lyrics-table td {
    border: 0;
    padding: 4px 12px;
  }

  .lyrics-table th::before,
  .lyrics-table td::before {
    content: attr(data-label) ': ';
    color: var(--color-muted);
    font-family: var(--font-label);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
}
</style>
