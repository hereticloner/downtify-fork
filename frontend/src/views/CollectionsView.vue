<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <h1 class="text-2xl font-semibold">{{ t('collections.title') }}</h1>

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

    <div v-if="error" class="text-sm text-red-500">{{ error }}</div>

    <div class="flex flex-col gap-3">
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
            <span
              v-for="pl in col.playlists"
              :key="pl"
              class="rounded-control border border-line-2 bg-surface px-2.5 py-1 text-sm"
            >
              {{ pl }}
            </span>
          </div>
          <span v-else class="text-sm text-faint">
            {{ t('collections.empty') }}
          </span>
        </div>
      </UiPanel>
      <p v-if="!collections.length && !loading" class="text-sm text-faint">
        {{ t('collections.none') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from '/src/i18n'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'

const { t } = useI18n()
const collections = ref([])
const newName = ref('')
const error = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await fetch('/api/collections')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    collections.value = (await resp.json()).map((c) => ({ ...c, _add: '' }))
  } catch (exc) {
    error.value = String(exc)
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!newName.value.trim()) return
  error.value = ''
  const resp = await fetch('/api/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName.value }),
  })
  if (!resp.ok) {
    error.value = (await resp.json()).detail || `HTTP ${resp.status}`
    return
  }
  newName.value = ''
  await load()
}

async function add(col) {
  if (!col._add.trim()) return
  error.value = ''
  const resp = await fetch(`/api/collections/${encodeURIComponent(col.name)}/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ add: [col._add] }),
  })
  if (!resp.ok) {
    error.value = (await resp.json()).detail || `HTTP ${resp.status}`
    return
  }
  col._add = ''
  await load()
}

async function remove(col) {
  if (!confirm(t('collections.confirmDelete', { name: col.name }))) return
  error.value = ''
  const resp = await fetch(
    `/api/collections/${encodeURIComponent(col.name)}`,
    { method: 'DELETE' }
  )
  if (!resp.ok) {
    error.value = (await resp.json()).detail || `HTTP ${resp.status}`
    return
  }
  await load()
}

onMounted(load)
</script>
