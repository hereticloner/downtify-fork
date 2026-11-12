<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('trash.title')"
      :subtitle="t('trash.subtitle', { days: capability.retentionDays.value })"
      class="border-b-2 border-line"
    >
      <UiButton variant="secondary" icon="library" :to="{ name: 'Library' }">
        {{ t('library.backToLibrary') }}
      </UiButton>
      <UiButton
        v-if="ready"
        variant="secondary"
        icon="refresh"
        :loading="loading"
        @click="load"
      >
        <span class="max-sm:sr-only">{{ t('common.refresh') }}</span>
      </UiButton>
    </PageHeader>

    <div v-if="!auth.isAdmin.value" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="lock"
        :title="t('trash.adminOnly')"
        :body="t('trash.adminOnlyHint')"
      />
    </div>
    <div
      v-else-if="checked && !capability.enabled.value"
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="trash"
        :title="t('trash.off')"
        :body="t('trash.offHint')"
      />
    </div>

    <template v-else-if="ready">
      <div
        class="flex flex-wrap items-center gap-2 border-b-2 border-line px-4 py-2"
      >
        <UiSegmented v-model="view" :options="views" show-labels />
        <label
          v-if="view === 'trash'"
          class="flex h-9 min-w-0 flex-1 basis-56 items-center gap-2 border-2 border-line-2 px-2.5 transition-colors duration-100 focus-within:border-accent sm:max-w-xs"
        >
          <AppIcon name="filter" :size="15" class="text-faint" />
          <span class="sr-only">{{ t('trash.search') }}</span>
          <input
            v-model="search"
            type="search"
            :placeholder="t('trash.search')"
            class="h-full min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint"
          />
        </label>
        <UiButton
          v-if="view === 'trash' && selected.length"
          variant="primary"
          icon="retry"
          :loading="busy"
          @click="restore(selected)"
        >
          {{ t('trash.restoreSelected', { count: selected.length }) }}
        </UiButton>
      </div>

      <p
        v-if="error"
        role="alert"
        class="border-b-2 border-line bg-surface-2 px-4 py-2 text-[13px] text-danger"
      >
        {{ error }}
      </p>

      <template v-if="view === 'trash'">
        <div
          class="flex flex-wrap items-center gap-x-4 gap-y-1 border-b-2 border-line px-4 py-2"
        >
          <span class="mono tabular text-muted" aria-live="polite">
            {{ t('trash.summary', { count: total, size: formatBytes(size) }) }}
          </span>
          <span class="mono tabular ml-auto text-faint"
            >{{ items.length }} / {{ total }}</span
          >
        </div>

        <div
          v-if="!items.length && !loading"
          class="border-b-2 border-line p-4"
        >
          <UiEmpty
            icon="trash"
            :title="search ? t('trash.noMatch') : t('trash.empty')"
            :body="search ? '' : t('trash.emptyHint')"
          />
        </div>

        <!-- Deleted artefacts: 56px rows, square checkbox, mono dates. -->
        <div v-else class="border-b-2 border-line">
          <div
            class="hidden h-9 items-center gap-3 border-b-2 border-line bg-surface-2 px-3 lg:grid lg:grid-cols-[28px_minmax(0,2.2fr)_200px_88px_104px]"
          >
            <span aria-hidden="true" />
            <span class="eyebrow">{{ t('track.title') }}</span>
            <span aria-hidden="true" />
            <span class="eyebrow text-right">{{ t('track.size') }}</span>
            <span aria-hidden="true" />
          </div>

          <ul class="flex flex-col">
            <li
              v-for="item in items"
              :key="item.id"
              class="grid min-h-14 grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 border-b border-line-2 px-3 py-2 transition-colors duration-100 last:border-b-0 hover:bg-surface-2 lg:grid-cols-[28px_minmax(0,2.2fr)_200px_88px_104px] lg:gap-3 lg:py-0"
            >
              <button
                type="button"
                role="checkbox"
                :aria-checked="selected.includes(item.id)"
                :aria-label="t('trash.select', { title: titleOf(item) })"
                :disabled="!restorable(item) || busy"
                class="flex size-11 items-center justify-center disabled:cursor-not-allowed lg:size-7"
                @click="toggleSelect(item)"
              >
                <span
                  class="flex size-4 items-center justify-center border-2 transition-colors duration-100"
                  :class="
                    selected.includes(item.id)
                      ? 'border-line bg-invert text-on-invert'
                      : 'border-line-3'
                  "
                >
                  <AppIcon
                    v-if="selected.includes(item.id)"
                    name="check"
                    :size="10"
                    stroke-width="3"
                  />
                </span>
              </button>

              <div class="flex min-w-0 items-center gap-3" :title="item.file">
                <CoverArt
                  :name="item.metadata?.album || titleOf(item)"
                  :letter-size="12"
                  :icon-size="15"
                  class="size-10"
                />
                <div class="min-w-0">
                  <p class="truncate text-[13px] font-semibold text-fg">
                    {{ titleOf(item) }}
                  </p>
                  <p class="truncate text-[12px] text-muted">
                    {{ item.metadata.artist || '—' }}
                    <span class="mono ml-1.5 border border-line-2 px-1">{{
                      formatOf(item)
                    }}</span>
                  </p>
                  <p v-if="item.error" class="mono mt-1 text-danger">
                    {{ t(trashErrorKey(item.error)) }}
                  </p>
                </div>
              </div>

              <div class="flex items-center justify-end gap-1 lg:order-last">
                <UiIconButton
                  v-if="item.state === 'error'"
                  icon="refresh"
                  :label="t('trash.retry')"
                  size="sm"
                  :disabled="busy"
                  @click="retry(item.id)"
                />
                <UiIconButton
                  v-if="restorable(item)"
                  icon="retry"
                  :label="t('trash.restore')"
                  size="sm"
                  :disabled="busy"
                  @click="restore([item.id])"
                />
              </div>

              <div
                class="col-span-2 flex flex-wrap items-center gap-x-3 gap-y-1 lg:contents"
              >
                <div class="flex min-w-0 flex-col gap-1">
                  <UiBadge :tone="STATE_TONES[item.state] || 'neutral'">
                    {{ t('trash.states.' + item.state) }}
                  </UiBadge>
                  <span
                    v-if="item.expires_at && item.state === 'trashed'"
                    class="mono text-faint"
                  >
                    {{ t('trash.keptUntil', { date: date(item.expires_at) }) }}
                  </span>
                </div>
                <span class="mono tabular text-muted lg:text-right">{{
                  formatBytes(item.size)
                }}</span>
              </div>
            </li>
          </ul>
        </div>

        <div
          v-if="total > PAGE"
          class="flex items-center justify-end gap-2 border-b-2 border-line px-4 py-2"
        >
          <span class="mono tabular mr-auto text-faint">{{
            Math.floor(offset / PAGE) + 1
          }}</span>
          <UiButton
            size="sm"
            variant="secondary"
            icon="chevron-left"
            :disabled="offset === 0 || busy"
            @click="offset -= PAGE"
          >
            {{ t('trash.previous') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="secondary"
            icon-right="chevron-right"
            :disabled="offset + PAGE >= total || busy"
            @click="offset += PAGE"
          >
            {{ t('trash.next') }}
          </UiButton>
        </div>
      </template>

      <template v-else>
        <p
          class="border-b-2 border-line px-4 py-2 text-[13px] text-pretty text-muted"
        >
          {{ t('trash.exclusionsHint') }}
        </p>
        <div
          v-if="!exclusions.length && !loading"
          class="border-b-2 border-line p-4"
        >
          <UiEmpty icon="download" :title="t('trash.exclusionsEmpty')" />
        </div>
        <ul v-else class="flex flex-col border-b-2 border-line">
          <li
            v-for="item in exclusions"
            :key="item.id"
            class="flex min-h-14 flex-wrap items-center gap-x-3 gap-y-1 border-b border-line-2 px-4 py-2 last:border-b-0"
          >
            <div class="min-w-0 flex-1 basis-56">
              <p class="truncate text-[13px] font-semibold text-fg">
                {{ titleOf(item) }}
              </p>
              <p class="mono truncate text-muted">
                {{ item.metadata.artist || '—' }} · {{ formatOf(item) }}
              </p>
            </div>
            <UiButton
              size="sm"
              icon="download"
              :disabled="busy"
              @click="allow(item)"
            >
              {{ t('trash.allowDownload') }}
            </UiButton>
          </li>
        </ul>
      </template>
    </template>
  </div>
</template>

<script setup>
// The music trash (admins): songs moved out of the library, kept for a
// while and restorable until then, and the expired ones still kept out
// of automatic downloads. Reads /api/v1/library/trash; the moves
// themselves are done by the server's trash worker, so a request shows
// as waiting until the worker has really done it.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { formatBytes } from '/src/lib/format'
import {
  STATE_TONES,
  restorable,
  trashError,
  trashErrorKey,
  useTrashCapability,
} from '/src/lib/trash'
import { useI18n } from '/src/i18n'

const PAGE = 50
const POLL_MS = 3000

const { t, locale } = useI18n()
const auth = useAuth()
const ui = useUi()
const library = useLibrary()
const capability = useTrashCapability()

const view = ref('trash')
const items = ref([])
const exclusions = ref([])
const selected = ref([])
const total = ref(0)
const size = ref(0)
const offset = ref(0)
const search = ref('')
const error = ref('')
const loading = ref(false)
const busy = ref(false)
const checked = ref(false)
let timer = null
let debounce = null
let disposed = false

const ready = computed(
  () => auth.isAdmin.value && checked.value && capability.canManage.value
)
const views = computed(() => [
  { value: 'trash', label: t('trash.inTrash'), icon: 'trash' },
  { value: 'exclusions', label: t('trash.exclusions'), icon: 'download' },
])

const date = (seconds) =>
  new Date(seconds * 1000).toLocaleDateString(locale.value, {
    dateStyle: 'medium',
  })
const titleOf = (item) => item.metadata?.title || item.file
const formatOf = (item) =>
  String(item.metadata?.codec || item.file.split('.').pop() || '').toUpperCase()

/** The square checkbox: same multi-select list the native input held. */
function toggleSelect(item) {
  if (!restorable(item) || busy.value) return
  selected.value = selected.value.includes(item.id)
    ? selected.value.filter((id) => id !== item.id)
    : [...selected.value, item.id]
}

async function load() {
  if (loading.value || !ready.value || disposed) return
  loading.value = true
  try {
    if (view.value === 'trash') {
      const { data } = await API.trashList({
        offset: offset.value,
        limit: PAGE,
        search: search.value,
      })
      if (disposed) return
      items.value = data.items
      total.value = data.total
      size.value = data.size
      selected.value = selected.value.filter((id) =>
        data.items.some((item) => item.id === id && restorable(item))
      )
    } else {
      const { data } = await API.trashExclusions()
      if (disposed) return
      exclusions.value = data.items
    }
    error.value = ''
  } catch (e) {
    error.value = trashError(e, t)
  } finally {
    loading.value = false
  }
}

async function act(request) {
  busy.value = true
  error.value = ''
  try {
    await request()
    selected.value = []
    await load()
    await library.load({ force: true })
  } catch (e) {
    error.value = trashError(e, t)
  } finally {
    busy.value = false
  }
}

function restore(ids) {
  return act(() => API.trashRestore([...ids]))
}

function retry(id) {
  return act(() => API.trashRetry([id]))
}

async function allow(item) {
  const ok = await ui.confirm({
    title: t('trash.allowTitle', { title: titleOf(item) }),
    body: t('trash.allowBody'),
    confirmLabel: t('trash.allowDownload'),
  })
  if (ok) await act(() => API.trashAllowDownload([item.id]))
}

watch(search, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => {
    offset.value = 0
    load()
  }, 300)
})
watch([offset, view], load)

onMounted(async () => {
  await capability.refresh()
  checked.value = true
  load()
  timer = setInterval(() => {
    if (!document.hidden) load()
  }, POLL_MS)
})
onUnmounted(() => {
  disposed = true
  clearInterval(timer)
  clearTimeout(debounce)
})
</script>
