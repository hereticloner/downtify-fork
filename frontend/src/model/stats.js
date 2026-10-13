// The Stats tab's numbers: what /api/stats knows about the library, the
// downloads and what has been played. Module state like the other stores,
// so the page and every panel read the same answer.
import { ref } from 'vue'

import API from '/src/model/api'

const stats = ref({})
const loading = ref(true)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    const res = await API.getStats()
    // The Axios interceptor hands back the whole response. The panels
    // read `stats.library.tracks` and friends, so this has to be the
    // body - keeping the envelope leaves every panel on its `?? 0`
    // fallback and the tab looks empty however full the library is.
    stats.value = res.data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

/** The Stats tab's data, plus the `load` the page calls on mount. */
export function useStats() {
  return { stats, loading, error, load }
}
