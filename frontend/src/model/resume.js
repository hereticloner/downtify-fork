import { ref } from 'vue'

import API from '/src/model/api'

const item = ref(null)
const loading = ref(false)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    const response = await API.getResume()
    item.value = response.data?.track ? response.data : null
  } catch {
    error.value = true
    item.value = null
  } finally {
    loading.value = false
  }
}

function dismiss() {
  item.value = null
}

export function useResume() {
  return { item, loading, error, load, dismiss }
}
