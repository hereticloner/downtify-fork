import { ref } from 'vue'

import API from '/src/model/api'

const items = ref([])
const loading = ref(false)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    const response = await API.getDownloadFailures()
    items.value = Array.isArray(response.data?.items) ? response.data.items : []
  } catch {
    error.value = true
    items.value = []
  } finally {
    loading.value = false
  }
}

async function retry(songId) {
  await API.retryDownloadFailure(songId)
  dismiss(songId)
}

async function clear() {
  await API.clearDownloadFailures()
  items.value = []
}

function dismiss(songId) {
  items.value = items.value.filter((row) => row.song_id !== songId)
}

export function useDownloadFailures() {
  return { items, loading, error, load, retry, clear, dismiss }
}
