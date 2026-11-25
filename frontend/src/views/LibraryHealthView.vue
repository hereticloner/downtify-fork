<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('libraryHealth.title')"
      :subtitle="t('libraryHealth.subtitle')"
      class="border-b-2 border-line"
    >
      <UiButton
        v-if="auth.isAdmin.value && report"
        variant="secondary"
        icon="download"
        :loading="exporting"
        @click="downloadExport"
      >
        {{ t('libraryHealth.export') }}
      </UiButton>
      <UiButton
        v-if="auth.isAdmin.value"
        variant="primary"
        icon="refresh"
        :loading="loading"
        @click="load"
      >
        {{ t('libraryHealth.scan') }}
      </UiButton>
    </PageHeader>

    <div v-if="!auth.isAdmin.value" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="lock"
        :title="t('libraryHealth.adminOnly')"
        :body="t('libraryHealth.adminOnlyHint')"
      />
    </div>

    <p v-else-if="error" role="alert" class="border-b-2 border-line p-4">
      <UiEmpty icon="alert" :title="t('libraryHealth.loadFailed')">
        <UiButton icon="refresh" @click="load">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </p>

    <template v-else-if="report">
      <section
        class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 xl:grid-cols-5"
        :aria-label="t('libraryHealth.summary')"
      >
        <div
          v-for="category in CATEGORY_KEYS"
          :key="category"
          class="border-r-2 border-b-2 border-line px-4 py-3"
        >
          <div class="mono tabular text-[28px] leading-none font-bold">
            {{ counts[category] }}
          </div>
          <div class="eyebrow mt-2 text-muted">
            {{ t('libraryHealth.categories.' + category) }}
          </div>
        </div>
      </section>

      <div class="border-b-2 border-line px-3 py-1">
        <UiChips
          :items="categoryItems"
          v-model="category"
          :aria-label="t('libraryHealth.filter')"
        />
      </div>

      <div
        v-if="report.scanned_at"
        class="mono flex flex-wrap items-center gap-x-4 border-b border-line-2 px-4 py-2 text-faint"
      >
        <span>{{
          t('libraryHealth.scannedAt', { date: formattedScannedAt })
        }}</span>
        <span v-if="report.warnings.length" class="text-danger">
          {{ t('libraryHealth.partial') }}
        </span>
      </div>

      <div v-if="!visibleFindings.length" class="border-b-2 border-line p-4">
        <UiEmpty
          :icon="category === 'all' ? 'check' : 'filter'"
          :title="
            category === 'all'
              ? t('libraryHealth.healthy')
              : t('libraryHealth.noMatches')
          "
          :body="
            category === 'all'
              ? t('libraryHealth.healthyHint')
              : t('libraryHealth.noMatchesHint')
          "
        >
          <UiButton
            v-if="category !== 'all'"
            variant="ghost"
            @click="category = 'all'"
          >
            {{ t('libraryHealth.clearFilter') }}
          </UiButton>
        </UiEmpty>
      </div>

      <div
        v-else
        role="region"
        tabindex="0"
        :aria-label="t('libraryHealth.findings')"
        class="health-table-wrap border-b-2 border-line"
      >
        <table class="health-table">
          <caption class="sr-only">
            {{
              t('libraryHealth.findings')
            }}
          </caption>
          <thead>
            <tr>
              <th scope="col">{{ t('libraryHealth.category') }}</th>
              <th scope="col">{{ t('libraryHealth.source') }}</th>
              <th scope="col">{{ t('libraryHealth.file') }}</th>
              <th scope="col">{{ t('libraryHealth.recommendation') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="finding in visibleFindings" :key="finding.id">
              <td data-label="Category">
                <span class="eyebrow">{{
                  t('libraryHealth.categories.' + finding.category)
                }}</span>
              </td>
              <td data-label="Source">
                {{ t('libraryHealth.sources.' + finding.source) }}
              </td>
              <th scope="row" data-label="File">
                <span class="mono block truncate" :title="finding.file">{{
                  finding.file || '—'
                }}</span>
              </th>
              <td data-label="Recommendation">
                {{
                  t('libraryHealth.recommendations.' + finding.recommendation)
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="px-4 py-3 text-[13px] text-pretty text-muted">
        {{ t('libraryHealth.readOnly') }}
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
import { useI18n } from '/src/i18n'
import { useAuth } from '/src/model/auth'
import {
  CATEGORY_KEYS,
  categoryCounts,
  filterFindings,
} from '/src/lib/libraryHealth'
import {
  exportLibraryHealth,
  scanLibraryHealth,
} from '/src/model/libraryHealth'

const { t, locale } = useI18n()
const auth = useAuth()
const report = ref(null)
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const category = ref('all')

const counts = computed(() => categoryCounts(report.value))
const visibleFindings = computed(() =>
  filterFindings(report.value?.findings, category.value)
)
const categoryItems = computed(() => [
  {
    id: 'all',
    label: t('libraryHealth.categories.all'),
    count: report.value?.summary?.findings || 0,
  },
  ...CATEGORY_KEYS.map((key) => ({
    id: key,
    label: t('libraryHealth.categories.' + key),
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
    report.value = await scanLibraryHealth()
  } catch {
    error.value = t('libraryHealth.loadFailed')
  } finally {
    loading.value = false
  }
}

async function downloadExport() {
  exporting.value = true
  try {
    const blob = await exportLibraryHealth()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = t('libraryHealth.exportFilename')
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    error.value = t('libraryHealth.exportFailed')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  if (auth.isAdmin.value) void load()
})
</script>

<style scoped>
.health-table-wrap {
  container-type: inline-size;
  overflow: auto;
  max-block-size: min(70vh, 720px);
}

.health-table {
  min-inline-size: 760px;
  border-collapse: separate;
  border-spacing: 0;
}

.health-table th,
.health-table td {
  border-bottom: 1px solid var(--color-line-2);
  padding: 10px 12px;
  text-align: start;
  vertical-align: top;
}

.health-table thead th {
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

.health-table tbody tr:hover {
  background: var(--color-surface-2);
}

@container (width < 600px) {
  .health-table {
    min-inline-size: 0;
  }

  .health-table thead {
    display: none;
  }

  .health-table,
  .health-table tbody,
  .health-table tr,
  .health-table th,
  .health-table td {
    display: block;
  }

  .health-table tbody tr {
    border-bottom: 2px solid var(--color-line);
    padding-block: 8px;
  }

  .health-table th,
  .health-table td {
    border: 0;
    padding: 4px 12px;
  }

  .health-table td::before,
  .health-table tbody th::before {
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
