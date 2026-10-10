// Deezer's global "what's trending" chart, for the Charts page.
import { ref } from 'vue'

import API from '/src/model/api'
import { t } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'

const tracks = ref([])
const albums = ref([])
const artists = ref([])
const playlists = ref([])
const loading = ref(false)
const error = ref('')
let loaded = false

async function load({ force = false } = {}) {
  if (loaded && !force) return
  loading.value = true
  error.value = ''
  try {
    const res = await API.getChart()
    tracks.value = res.data?.tracks || []
    albums.value = res.data?.albums || []
    artists.value = res.data?.artists || []
    playlists.value = res.data?.playlists || []
    loaded = true
  } catch (err) {
    error.value = friendlyError(t, err, 'charts.failed')
  } finally {
    loading.value = false
  }
}

export function useCharts() {
  return { tracks, albums, artists, playlists, loading, error, load }
}
