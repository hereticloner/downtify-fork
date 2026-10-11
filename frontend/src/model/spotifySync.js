// Spotify live sync status + manual trigger (see downtify/spotify_sync.py).
//
// The sync reuses the Spotify Mirror connection, so this module only
// reads the status (switch, interval, per-playlist last snapshot) and
// asks the server to run one sweep now when the user clicks "Sync now".
import { ref } from 'vue'

import API from '/src/model/api'

export function useSpotifySync() {
  const status = ref(null)
  const loading = ref(false)
  const running = ref(false)

  async function load() {
    loading.value = true
    try {
      const res = await API.getSpotifySync()
      status.value = res?.data || null
    } catch {
      status.value = null
    } finally {
      loading.value = false
    }
  }

  async function run() {
    running.value = true
    try {
      const res = await API.runSpotifySync()
      return res?.data || null
    } finally {
      running.value = false
    }
  }

  return { status, loading, running, load, run }
}
