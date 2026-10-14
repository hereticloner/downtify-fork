// Spotify Mirror actions and live status (see downtify/spotify_mirror.py).
import { computed, ref } from 'vue'

import { t } from '/src/i18n'
import API from '/src/model/api'

/**
 * Mirror one track's play to the connected Spotify device now, skipping
 * the mirror's own dedupe - it is an admin's manual test. `track` is a
 * library track row (`{ file, title, artist, ... }`).
 */
export async function mirrorNow(track) {
  const res = await API.spotifyMirrorNow(track)
  return res.data
}

// What the mirror is doing right now: the device it plays on, whether the
// token still works, and the last play each player managed. Module state
// like the other stores, so the panel and its poll read one answer.
//
// The endpoint is admin-only and the tracker behind it is in-memory, so a
// refused request - or a server that just restarted - clears the panel
// instead of raising anything: "nothing to show" is a valid reading.
const status = ref(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await API.getMirrorStatus()
    status.value = res?.data || null
  } catch {
    status.value = null
  } finally {
    loading.value = false
  }
}

/**
 * The newest of a tracker's `{"<user>:<player>": {…, at}}` map, or `null`
 * when nothing was recorded. The panel shows one line per map, so it
 * takes the newest entry rather than all of them - the last thing that
 * happened is the one that explains the play that "didn't show up".
 */
function newest(entries) {
  const rows = Object.values(entries || {})
  if (!rows.length) return null
  return rows.reduce((a, b) => (Number(b.at) > Number(a.at) ? b : a))
}

/** A tracker `at` (unix seconds) as a locale date, `''` if it isn't one. */
function when(at) {
  const date = new Date(Number(at) * 1000)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString()
}

// "Downtify Mirror (a1b2c3d4…)": the device the mirror plays on. A
// server with no connection has neither half, so the id falls back to
// what the endpoint was told to look for.
const device = computed(() => {
  const name = String(status.value?.device_name || '').trim()
  const id = String(status.value?.device_id || '').trim()
  if (!name) return id ? `${id}…` : ''
  return id ? `${name} (${id.slice(0, 8)}…)` : name
})

// The last play the mirror managed, and the reason the last one failed -
// the two lines that answer "why isn't this track in my history?".
const lastMirror = computed(() => {
  const entry = newest(status.value?.last_mirrors)
  if (!entry) return ''
  return t('settings.mirrorLast', {
    uri: entry.uri || '',
    when: when(entry.at),
  })
})

const lastError = computed(() => {
  const entry = newest(status.value?.last_errors)
  if (!entry) return ''
  return t('settings.mirrorLastError', {
    reason: entry.reason || '',
    when: when(entry.at),
  })
})

/** The mirror's live status, its `load`, and the lines the panel reads. */
export function useMirrorStatus() {
  return { status, loading, load, device, lastMirror, lastError }
}
