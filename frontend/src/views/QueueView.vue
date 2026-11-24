<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-5 px-4 pt-5 sm:px-6 md:pt-6 lg:px-8"
  >
    <PageHeader :title="t('queue.title')" :subtitle="subtitle">
      <template v-if="auth.isAdmin.value">
        <UiButton
          v-if="queuePause.paused.value"
          variant="primary"
          icon="play"
          :loading="queuePause.busy.value"
          @click="toggleQueue(queuePause.resume)"
        >
          {{ t('queue.resume') }}
        </UiButton>
        <UiButton
          v-else
          variant="secondary"
          icon="pause"
          :loading="queuePause.busy.value"
          @click="toggleQueue(queuePause.pause)"
        >
          {{ t('queue.pause') }}
        </UiButton>
      </template>
      <UiButton
        v-if="counts.failed"
        variant="ghost"
        icon="retry"
        @click="dm.retryAllFailed()"
      >
        {{ t('queue.retryFailed', { count: counts.failed }) }}
      </UiButton>
      <UiButton
        v-if="counts.done"
        variant="ghost"
        icon="check"
        @click="dm.clearCompleted()"
      >
        {{ t('queue.clearDone', { count: counts.done }) }}
      </UiButton>
      <UiButton
        v-if="queue.length"
        variant="danger"
        icon="trash"
        @click="clearAll"
      >
        <span class="max-sm:sr-only">{{ t('queue.clearAll') }}</span>
      </UiButton>
    </PageHeader>

    <div
      v-if="queuePause.paused.value"
      role="status"
      class="flex items-start gap-3 border-2 border-line bg-surface-2 p-3"
    >
      <AppIcon
        :name="queuePause.draining.value ? 'clock' : 'pause'"
        :size="18"
        class="mt-0.5 text-muted"
      />
      <div class="min-w-0">
        <p class="text-sm font-medium">
          {{
            queuePause.draining.value
              ? t('queue.pausingTitle')
              : t('queue.pausedTitle')
          }}
        </p>
        <p class="mt-0.5 text-[13px] text-muted">
          {{
            queuePause.draining.value
              ? t('queue.pausingBody', {
                  count: queuePause.status.active,
                })
              : t('queue.pausedBody')
          }}
          {{ t('queue.pausedKept') }}
        </p>
      </div>
    </div>

    <UiTabs :items="tabs" :model-value="tab" />

    <div
      v-if="auth.isAdmin.value && someSelected"
      role="group"
      :aria-label="t('queue.selectedActions')"
      class="flex flex-wrap items-center gap-2 border-2 border-line bg-surface-2 p-3"
    >
      <span role="status" class="me-auto text-[13px] font-medium">
        {{ t('queue.selectedCount', { count: selectedIds.length }) }}
      </span>
      <UiButton
        size="sm"
        variant="secondary"
        :disabled="queueBusy"
        @click="setSelectedPriority('high')"
      >
        {{ t('queue.priorityHigh') }}
      </UiButton>
      <UiButton
        size="sm"
        variant="secondary"
        :disabled="queueBusy"
        @click="setSelectedPriority('normal')"
      >
        {{ t('queue.priorityNormal') }}
      </UiButton>
      <UiButton
        size="sm"
        variant="secondary"
        icon="pause"
        :disabled="queueBusy || !canPauseSelected"
        @click="bulkAction('pause')"
      >
        {{ t('queue.bulkPause') }}
      </UiButton>
      <UiButton
        size="sm"
        variant="secondary"
        icon="play"
        :disabled="queueBusy || !canResumeSelected"
        @click="bulkAction('resume')"
      >
        {{ t('queue.bulkResume') }}
      </UiButton>
      <UiButton
        size="sm"
        variant="danger"
        icon="trash"
        :disabled="queueBusy"
        @click="bulkAction('remove')"
      >
        {{ t('queue.bulkRemove') }}
      </UiButton>
      <UiButton
        size="sm"
        variant="ghost"
        :disabled="queueBusy"
        @click="selected.clear()"
      >
        {{ t('queue.clearSelection') }}
      </UiButton>
    </div>

    <div class="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div class="flex min-w-0 flex-col">
        <UiEmpty
          v-if="!queue.length"
          icon="download"
          :title="t('queue.emptyTitle')"
          :body="t('queue.emptyBody')"
        >
          <UiButton variant="primary" icon="search" @click="ui.focusSearch()">
            {{ t('queue.emptyAction') }}
          </UiButton>
        </UiEmpty>

        <UiEmpty
          v-else-if="!items.length"
          :icon="tab === 'failed' ? 'check-circle' : 'clock'"
          :title="t(`queue.emptyTab.${tab}`)"
          :body="
            tab === 'active' && counts.queued
              ? queuePause.paused.value
                ? t('queue.pausedBody')
                : t('queue.waitingHint', { count: counts.queued })
              : ''
          "
        />

        <template v-else>
          <!-- Table head: the open tab and how many rows it holds. -->
          <div
            class="flex h-10 items-stretch border-2 border-b-0 border-line bg-surface-2"
          >
            <label
              v-if="auth.isAdmin.value && selectableIds.length"
              class="flex size-11 shrink-0 items-center justify-center border-r-2 border-line-2"
            >
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected && !allSelected"
                class="size-4 accent-accent"
                @change="toggleSelectAll"
              />
              <span class="sr-only">{{ t('queue.selectAll') }}</span>
            </label>
            <span class="eyebrow flex min-w-0 flex-1 items-center px-3 text-fg">
              {{ tabs.find((entry) => entry.id === tab)?.label }}
            </span>
            <span
              class="mono tabular flex shrink-0 items-center border-l-2 border-line px-3 text-fg-3"
            >
              {{ items.length }}
            </span>
          </div>

          <div
            ref="listRoot"
            class="relative border-2 border-line"
            :style="{ height: `${totalSize}px` }"
          >
            <div
              v-for="row in rows"
              :key="row.item.key"
              :ref="measureRow"
              :data-index="row.index"
              class="absolute inset-x-0 top-0"
              :style="{ transform: `translateY(${row.start}px)` }"
            >
              <QueueItem
                :item="row.item"
                :compact="
                  row.item.state === 'queued' || row.item.state === 'done'
                "
                :selected="selected.has(row.item.key)"
                :selection-active="auth.isAdmin.value"
                @select="toggleSelected"
                @priority="setPriority"
              />
            </div>
          </div>
        </template>
      </div>

      <aside class="flex flex-col gap-4 xl:sticky xl:top-[104px]">
        <FailureCenter />
        <DownloadExclusions />
        <UiPanel
          v-if="activeBatches.length"
          :title="t('queue.playlistDownloads')"
        >
          <ul class="flex flex-col gap-4">
            <li v-for="batch in activeBatches" :key="batch.spotify_playlist_id">
              <RouterLink
                :to="{ name: 'Playlist', query: { name: batch.playlist_name } }"
                class="flex items-center justify-between gap-3 text-sm"
              >
                <span class="truncate font-medium hover:underline">{{
                  batch.playlist_name
                }}</span>
                <span class="mono tabular shrink-0 text-muted">
                  {{ batch.downloaded_count }} / {{ batch.expected_count }}
                </span>
              </RouterLink>
              <UiProgress
                class="mt-2"
                :value="
                  batch.expected_count
                    ? (batch.downloaded_count / batch.expected_count) * 100
                    : 0
                "
              />
            </li>
          </ul>
        </UiPanel>

        <UiPanel
          v-if="incomplete.length"
          :title="t('queue.incompleteTitle')"
          :description="t('queue.incompleteHint')"
        >
          <ul class="flex flex-col gap-3">
            <li
              v-for="pl in incomplete"
              :key="pl.spotify_playlist_id"
              class="flex flex-wrap items-center gap-2 border-b border-line-2 pb-3 last:border-b-0 last:pb-0"
            >
              <RouterLink
                :to="{ name: 'Playlist', query: { name: pl.playlist_name } }"
                class="min-w-0 flex-1 truncate text-sm font-medium hover:underline"
              >
                {{ pl.playlist_name }}
              </RouterLink>
              <span class="mono tabular shrink-0 text-warn">
                {{ t('playlists.missingShort', { count: pl.missing_count }) }}
              </span>
              <UiButton
                size="sm"
                variant="ghost"
                icon="download"
                :loading="incompleteDownloading === pl.spotify_playlist_id"
                @click="downloadMissing(pl)"
              >
                {{
                  t('playlists.downloadMissing', { count: pl.missing_count })
                }}
              </UiButton>
            </li>
          </ul>
        </UiPanel>

        <UiPanel v-if="queue.length" :title="t('queue.sources')">
          <ul class="flex flex-col">
            <li
              v-for="source in sourceCounts"
              :key="source.id"
              class="flex items-center justify-between gap-3 border-b border-line-2 py-2 last:border-b-0"
            >
              <SourceBadge :source="source.id" />
              <span class="mono tabular text-muted">{{ source.count }}</span>
            </li>
            <li v-if="!sourceCounts.length" class="text-[13px] text-muted">
              {{ t('queue.noSourcesYet') }}
            </li>
          </ul>
        </UiPanel>

        <UiPanel
          :title="t('queue.importTitle')"
          :description="t('queue.importHint')"
        >
          <CsvImport />
        </UiPanel>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import SourceBadge from '/src/components/ui/SourceBadge.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import QueueItem from '/src/components/queue/QueueItem.vue'
import DownloadExclusions from '/src/components/queue/DownloadExclusions.vue'
import FailureCenter from '/src/components/queue/FailureCenter.vue'
import CsvImport from '/src/components/queue/CsvImport.vue'
import {
  useDownloadManager,
  useProgressTracker,
  syncQueueFromServer,
} from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useAuth } from '/src/model/auth'
import { useQueuePause } from '/src/model/queuePause'
import {
  downloadMissingPlaylistTracks,
  loadIncompletePlaylists,
} from '/src/model/incompletePlaylists'
import { useUi } from '/src/model/ui'
import API from '/src/model/api'
import { queueRowEstimate } from '/src/lib/queueList'
import {
  queueBulkRequest,
  queuePriorityRequest,
  selectableQueueIds,
  sortQueueItems,
} from '/src/lib/queueControl'
import { shouldJumpToActive } from '/src/lib/queueTab'
import { friendlyError } from '/src/lib/errors'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuth()
const queuePause = useQueuePause()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const library = useLibrary()
const ui = useUi()
const listRoot = ref(null)
const scrollMargin = ref(0)
const selected = ref(new Set())
const queueBusy = ref(false)

syncQueueFromServer().catch(() => {})
queuePause.refresh().catch(() => {})

const queue = computed(() => {
  tracker.queueVersion.value
  return tracker.downloadQueue.value
})

const counts = computed(() => {
  const result = { active: 0, queued: 0, done: 0, failed: 0 }
  for (const item of queue.value) result[item.state] += 1
  return result
})

const TABS = ['active', 'queued', 'done', 'failed', 'all']
const tab = computed(() => {
  const requested = String(route.params.tab || '')
  if (TABS.includes(requested)) return requested
  return counts.value.active || counts.value.queued ? 'active' : 'all'
})

// Jump to "In progress" as soon as downloads start.
watch(
  () => counts.value.active,
  (now, before) => {
    if (shouldJumpToActive(now, before, tab.value)) {
      router.replace({ name: 'Queue', params: { tab: 'active' } })
    }
  }
)

const tabs = computed(() =>
  [
    ['active', t('queue.tabActive'), counts.value.active],
    ['queued', t('queue.tabQueued'), counts.value.queued],
    ['done', t('queue.tabDone'), counts.value.done],
    ['failed', t('queue.tabFailed'), counts.value.failed],
    ['all', t('queue.tabAll'), queue.value.length],
  ].map(([id, label, count]) => ({
    id,
    label,
    count,
    to: { name: 'Queue', params: { tab: id } },
  }))
)

const ORDER = { active: 0, failed: 1, queued: 2, done: 3 }

const items = computed(() => {
  const ordered = sortQueueItems(queue.value)
  if (tab.value === 'all') {
    return ordered.sort((a, b) => ORDER[a.state] - ORDER[b.state])
  }
  const list = ordered.filter((item) => item.state === tab.value)
  // Newest finished first.
  return tab.value === 'done'
    ? list.sort((a, b) => b.updatedAt - a.updatedAt)
    : list
})

const selectableIds = computed(() => selectableQueueIds(items.value))
const selectedIds = computed(() => [...selected.value])
const selectedItems = computed(() =>
  queue.value.filter((item) => selected.value.has(item.key))
)
const allSelected = computed(
  () =>
    selectableIds.value.length > 0 &&
    selectableIds.value.every((id) => selected.value.has(id))
)
const someSelected = computed(() => selectedIds.value.length > 0)
const canPauseSelected = computed(() =>
  selectedItems.value.some((item) => item.web_status !== 'Paused')
)
const canResumeSelected = computed(() =>
  selectedItems.value.some((item) => item.web_status === 'Paused')
)

watch(selectableIds, (ids) => {
  const allowed = new Set(ids)
  const kept = [...selected.value].filter((id) => allowed.has(id))
  if (kept.length !== selected.value.size) selected.value = new Set(kept)
})

const virtualizer = useWindowVirtualizer(
  computed(() => ({
    count: items.value.length,
    estimateSize: (index) => queueRowEstimate(items.value[index]?.state),
    overscan: 8,
    scrollMargin: scrollMargin.value,
  }))
)

function measureOffset() {
  if (!listRoot.value) return
  scrollMargin.value =
    listRoot.value.getBoundingClientRect().top + window.scrollY
}

function measureRow(el) {
  if (el) virtualizer.value.measureElement(el)
}

onMounted(measureOffset)
watch(
  () => [tab.value, items.value.length],
  () => requestAnimationFrame(measureOffset)
)

const totalSize = computed(() => virtualizer.value.getTotalSize())
const rows = computed(() =>
  virtualizer.value
    .getVirtualItems()
    .map((row) => ({
      item: items.value[row.index],
      index: row.index,
      start: row.start - scrollMargin.value,
    }))
    .filter((row) => row.item)
)

const subtitle = computed(() => {
  if (!queue.value.length) return ''
  return [
    t('queue.countActive', { count: counts.value.active }),
    t('queue.countQueued', { count: counts.value.queued }),
    counts.value.failed
      ? t('queue.countFailed', { count: counts.value.failed })
      : '',
  ]
    .filter(Boolean)
    .join(' · ')
})

const sourceCounts = computed(() => {
  const map = new Map()
  for (const item of queue.value) {
    if (item.state !== 'done' || !item.provider) continue
    map.set(item.provider, (map.get(item.provider) || 0) + 1)
  }
  return [...map.entries()]
    .map(([id, count]) => ({ id, count }))
    .sort((a, b) => b.count - a.count)
})

const activeBatches = computed(() =>
  library.batches.value.filter(
    (batch) => batch.active_in_queue || batch.status === 'in_progress'
  )
)

// Tracked playlists that are still missing tracks, with a one-click way
// to finish them (see `GET /api/playlists/incomplete`).
const incomplete = ref([])
const incompleteDownloading = ref('')

async function loadIncomplete() {
  try {
    // Only playlists with something to do that isn't already downloading
    // (those are shown by the Playlist downloads panel above).
    incomplete.value = (await loadIncompletePlaylists()).filter(
      (pl) => Number(pl.missing_count) > 0 && !pl.active_in_queue
    )
  } catch {
    incomplete.value = []
  }
}

async function downloadMissing(pl) {
  incompleteDownloading.value = pl.spotify_playlist_id
  try {
    const res = await downloadMissingPlaylistTracks(pl)
    const count = Number(res?.missing_count ?? res?.count ?? 0)
    if (count) {
      ui.toast(t('toast.queuedMissing', { count }), { kind: 'success' })
      syncQueueFromServer().catch(() => {})
    } else {
      ui.toast(t('toast.playlistComplete'), { kind: 'success' })
    }
    await loadIncomplete()
  } catch (err) {
    ui.toast(friendlyError(t, err, 'toast.actionFailed'), { kind: 'error' })
  } finally {
    incompleteDownloading.value = ''
  }
}

// Keep playlist progress fresh while something is downloading.
watch(
  () => counts.value.done,
  () => {
    library.refreshSoon(1500)
    loadIncomplete()
  }
)

onMounted(loadIncomplete)

function toggleSelected(songId) {
  const next = new Set(selected.value)
  if (next.has(songId)) next.delete(songId)
  else next.add(songId)
  selected.value = next
}

function toggleSelectAll() {
  selected.value = allSelected.value ? new Set() : new Set(selectableIds.value)
}

async function refreshQueue() {
  await syncQueueFromServer()
}

async function setSelectedPriority(priority) {
  if (!selectedIds.value.length) return
  queueBusy.value = true
  try {
    await API.setQueuePriority(
      queuePriorityRequest(selectedIds.value, priority)
    )
    await refreshQueue()
    ui.toast(t('toast.queueUpdated'), { kind: 'success' })
  } catch (err) {
    ui.toast(friendlyError(t, err, 'toast.queueActionFailed'), {
      kind: 'error',
    })
  } finally {
    queueBusy.value = false
  }
}

async function setPriority(item, priority) {
  if (item.priority === priority) return
  queueBusy.value = true
  try {
    await API.setQueuePriority(queuePriorityRequest([item.key], priority))
    await refreshQueue()
    ui.toast(t('toast.queueUpdated'), { kind: 'success' })
  } catch (err) {
    ui.toast(friendlyError(t, err, 'toast.queueActionFailed'), {
      kind: 'error',
    })
  } finally {
    queueBusy.value = false
  }
}

async function bulkAction(action) {
  if (!selectedIds.value.length) return
  queueBusy.value = true
  try {
    await API.bulkQueueAction(queueBulkRequest(action, selectedIds.value))
    if (action === 'remove') {
      for (const item of selectedItems.value) tracker.removeSong(item.song)
      selected.value = new Set()
    }
    await refreshQueue()
    ui.toast(t('toast.queueUpdated'), { kind: 'success' })
  } catch (err) {
    ui.toast(friendlyError(t, err, 'toast.queueActionFailed'), {
      kind: 'error',
    })
  } finally {
    queueBusy.value = false
  }
}

async function toggleQueue(change) {
  try {
    await change()
  } catch {
    ui.toast(t('queue.pauseFailed'), { kind: 'error' })
  }
}

async function clearAll() {
  const ok = await ui.confirm({
    title: t('confirm.clearQueueTitle'),
    body: t('confirm.clearQueueBody'),
    confirmLabel: t('queue.clearAll'),
    danger: true,
  })
  if (ok) await dm.clearAll()
}
</script>
