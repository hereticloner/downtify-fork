// The Stats tab's numbers: what /api/stats knows about the library, the
// downloads and what has been played. Module state like the other stores,
// so the page and every panel read the same answer.
import { ref } from 'vue'

import API from '/src/model/api'

const stats = ref({})
const loading = ref(true)
const error = ref(false)
const dayLoading = ref(false)
const dayError = ref(false)
const days = ref(30)
let requestSequence = 0

export function playsForDay(value, selectedDate) {
  const playback = value?.playback || {}
  if (!selectedDate) return playback.recent || []
  return playback.day?.date === selectedDate ? playback.day.plays || [] : []
}

async function load(selectedDate = '', { background = false } = {}) {
  const request = ++requestSequence
  if (background) {
    dayLoading.value = true
    dayError.value = false
  } else {
    loading.value = true
    error.value = false
    dayLoading.value = false
    dayError.value = false
  }
  const params = { days: days.value, scope: 'user' }
  if (selectedDate) params.date = selectedDate
  try {
    const res = await API.getStats(params)
    // The Axios interceptor hands back the whole response. The panels
    // read `stats.library.tracks` and friends, so this has to be the
    // body - keeping the envelope leaves every panel on its `?? 0`
    // fallback and the tab looks empty however full the library is.
    if (request === requestSequence) stats.value = res.data
  } catch {
    if (request !== requestSequence) return
    if (background) dayError.value = true
    else error.value = true
  } finally {
    if (request === requestSequence) {
      loading.value = false
      dayLoading.value = false
    }
  }
}

/** The Stats tab's data, plus the `load` the page calls on mount. */
export function useStats() {
  return { stats, loading, error, dayLoading, dayError, days, load }
}
