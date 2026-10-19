// Spotify live sync status + manual trigger (see downtify/spotify_sync.py).
//
// The sync reuses the Spotify Mirror connection, so this module only
// reads the status (switch, interval, per-playlist last snapshot) and
// asks the server to run one sweep now when the user clicks "Sync now".
//
// It also listens for the background sweep's `spotify_sync` events: a
// rate limit the loop hit is invisible everywhere else — Settings shows
// it only after the user clicks the button — and measured 2026-10-19 a
// multi-hour one was reported as "the automatic sync stopped working",
// because nothing said so. One toast per cooldown, not one per
// two-minute wake-up.
import { ref } from 'vue'

import API from '/src/model/api'
import { t } from '/src/i18n'
import { useUi } from '/src/model/ui'

/** How long the same rate limit stays one toast. */
export const RATE_LIMIT_NOTICE_COOLDOWN_MS = 30 * 60 * 1000

let lastRateLimitNoticeAt = 0

/**
 * The minutes to announce for a `spotify_sync` event, or null when there
 * is nothing to say — a summary with no rate limit in it, or one that
 * already said it inside the cooldown.
 *
 * Exported for the tests, which drive the clock rather than wait.
 *
 * @param {unknown} data the WebSocket payload
 * @param {number} [now] ms clock
 * @returns {number | null} minutes until Spotify will answer again
 */
export function rateLimitNoticeMinutes(data, now = Date.now()) {
  if (data?.type !== 'spotify_sync') return null
  if (!(Number(data.rate_limited) > 0)) return null
  if (now - lastRateLimitNoticeAt < RATE_LIMIT_NOTICE_COOLDOWN_MS) {
    return null
  }
  lastRateLimitNoticeAt = now
  return Math.max(0, Math.round(Number(data.retry_after_minutes) || 0))
}

let listening = false

/**
 * Announce a rate limit the automatic sweep ran into. Called once from
 * the app shell, which is always mounted — the Settings page that owns
 * the rest of this feature is lazy.
 */
export function startRateLimitNotifier() {
  if (listening) return
  listening = true
  API.onMessage((data) => {
    const minutes = rateLimitNoticeMinutes(data)
    if (minutes == null) return
    useUi().toast(t('spotifySync.rateLimitedAuto', { minutes }), {
      kind: 'error',
      timeout: 8000,
    })
  })
}

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
