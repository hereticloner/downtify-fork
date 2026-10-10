<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('collections.title')" />

    <div class="flex items-center gap-2">
      <input
        v-model="newName"
        type="search"
        :placeholder="t('collections.placeholder')"
        class="h-10 min-w-0 flex-1 rounded-control border border-line-2 bg-surface px-3 text-sm outline-none placeholder:text-faint sm:max-w-xs"
        @keyup.enter="create"
      />
      <UiButton variant="primary" icon="plus" @click="create">
        {{ t('collections.create') }}
      </UiButton>
    </div>

    <div v-if="loading" class="flex flex-col gap-3" aria-busy="true">
      <UiSkeleton v-for="n in 3" :key="n" class="h-28 w-full !rounded-panel" />
    </div>

    <UiEmpty
      v-else-if="error"
      icon="alert"
      :title="t('library.loadFailed')"
      :body="t('library.loadFailedHint')"
    >
      <UiButton icon="refresh" @click="load">{{ t('common.retry') }}</UiButton>
    </UiEmpty>

    <div v-else class="flex flex-col gap-3">
      <UiPanel v-for="col in collections" :key="col.name" class="p-4">
        <div class="flex flex-wrap items-center gap-3">
          <h2 class="text-lg font-medium">{{ col.name }}</h2>
          <span class="text-sm text-faint">
            {{ col.playlists.length }}
          </span>
          <div class="ml-auto flex items-center gap-2">
            <input
              v-model="col._add"
              type="search"
              list="collection-playlist-names"
              :placeholder="t('collections.addPlaylist')"
              class="h-9 min-w-0 flex-1 rounded-control border border-line-2 bg-surface px-3 text-sm outline-none placeholder:text-faint sm:max-w-[16rem]"
              @keyup.enter="add(col)"
            />
            <UiButton
              variant="ghost"
              icon="trash"
              :title="t('common.delete')"
              @click="remove(col)"
            />
          </div>
        </div>
        <div class="mt-2 flex flex-wrap gap-2">
          <div v-if="col.playlists.length" class="flex flex-wrap gap-2">
            <router-link
              v-for="pl in col.playlists"
              :key="pl"
              :to="{ name: 'Playlist', query: { name: pl } }"
              class="rounded-control border border-line-2 bg-surface px-2.5 py-1 text-sm transition-colors hover:border-accent hover:text-accent"
            >
              {{ pl }}
            </router-link>
          </div>
          <span v-else class="text-sm text-faint">
            {{ t('collections.empty') }}
          </span>
        </div>
      </UiPanel>
      <p v-if="!collections.length" class="text-sm text-faint">
        {{ t('collections.none') }}
      </p>
    </div>

    <datalist id="collection-playlist-names">
      <option v-for="name in playlistNames" :key="name" :value="name" />
    </datalist>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from '/src/i18n'
import PageHeader from '/src/components/library/PageHeader.vue'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'

const { t } = useI18n()
const library = useLibrary()
const ui = useUi()
const collections = ref([])
const newName = ref('')
const error = ref(false)
const loading = ref(true)

// Names offered by the "add a playlist" box's native autocomplete - the
// same playlist list the Library page shows, so a name can't be typo'd.
const playlistNames = computed(() =>
  library.playlists.value
    .map((playlist) => String(playlist?.name || ''))
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b))
)

/** The backend's message for a failed request, or a generic one. */
async function failure(resp) {
  try {
    return (await resp.json()).detail || t('toast.actionFailed')
  } catch {
    return t('toast.actionFailed')
  }
}

async function load() {
  loading.value = true
  error.value = false
  try {
    const resp = await fetch('/api/collections')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    collections.value = (await resp.json()).map((c) => ({ ...c, _add: '' }))
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!newName.value.trim()) return
  const resp = await fetch('/api/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName.value }),
  })
  if (!resp.ok) {
    ui.toast(await failure(resp), { kind: 'error' })
    return
  }
  newName.value = ''
  await load()
}

async function add(col) {
  if (!col._add.trim()) return
  const resp = await fetch(
    `/api/collections/${encodeURIComponent(col.name)}/items`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ add: [col._add] }),
    }
  )
  if (!resp.ok) {
    ui.toast(await failure(resp), { kind: 'error' })
    return
  }
  col._add = ''
  await load()
}

async function remove(col) {
  const confirmed = await ui.confirm({
    title: t('collections.confirmDelete', { name: col.name }),
    confirmLabel: t('common.delete'),
    danger: true,
  })
  if (!confirmed) return
  const resp = await fetch(
    `/api/collections/${encodeURIComponent(col.name)}`,
    { method: 'DELETE' }
  )
  if (!resp.ok) {
    ui.toast(await failure(resp), { kind: 'error' })
    return
  }
  await load()
}

onMounted(() => {
  library.load()
  load()
})
</script>
