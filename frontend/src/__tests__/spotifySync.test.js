import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  onUnauthorized: () => () => {},
  onMessage: () => () => {},
  getAuthStatus: () =>
    Promise.resolve({
      data: { signed_in: true, user: { role: 'admin', username: 'me' } },
    }),
  getSettings: () => Promise.resolve({ data: {} }),
  setSettings: () => Promise.resolve({ data: {} }),
  getSpotifySync: vi.fn(),
  runSpotifySync: vi.fn(),
}))

vi.mock('/src/model/api', () => ({ default: api }))

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
}
globalThis.window = {
  location: { origin: 'http://localhost:8000' },
  matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  addEventListener: () => {},
  removeEventListener: () => {},
}

import { clampSyncIntervalMinutes, useSettingsManager } from '../model/settings'
import {
  RATE_LIMIT_NOTICE_COOLDOWN_MS,
  rateLimitNoticeMinutes,
  useSpotifySync,
} from '../model/spotifySync'

beforeEach(() => {
  api.getSpotifySync.mockReset()
  api.runSpotifySync.mockReset()
})

describe('Spotify Sync settings', () => {
  it('is off by default with an hour interval', () => {
    const { settings } = useSettingsManager()
    expect(settings.value.spotify_sync.enabled).toBe(false)
    expect(settings.value.spotify_sync.interval_minutes).toBe(60)
  })

  it('clamps the interval to the server bounds', () => {
    expect(clampSyncIntervalMinutes(0)).toBe(5)
    expect(clampSyncIntervalMinutes(10 ** 9)).toBe(7 * 24 * 60)
    expect(clampSyncIntervalMinutes('nonsense')).toBe(60)
    expect(clampSyncIntervalMinutes(90)).toBe(90)
  })
})

describe('useSpotifySync', () => {
  it('loads the status from the endpoint', async () => {
    api.getSpotifySync.mockResolvedValue({
      data: { enabled: true, connected: true, playlists: [] },
    })
    const sync = useSpotifySync()
    await sync.load()
    expect(sync.status.value.enabled).toBe(true)
    expect(sync.loading.value).toBe(false)
  })

  it('clears the status when the request fails', async () => {
    api.getSpotifySync.mockRejectedValue(new Error('nope'))
    const sync = useSpotifySync()
    await sync.load()
    expect(sync.status.value).toBe(null)
  })

  it('exposes the run summary and toggles its busy flag', async () => {
    api.runSpotifySync.mockResolvedValue({
      data: { changed: true, added: 2, removed: 1 },
    })
    const sync = useSpotifySync()
    const summary = await sync.run()
    expect(summary).toMatchObject({ changed: true, added: 2 })
    expect(sync.running.value).toBe(false)
  })
})

describe('the automatic sweep rate-limit notice', () => {
  const limited = (minutes) => ({
    type: 'spotify_sync',
    rate_limited: 1,
    retry_after_minutes: minutes,
  })
  const MIN = 60 * 1000
  const AFTER = RATE_LIMIT_NOTICE_COOLDOWN_MS

  // The module remembers when it last spoke; this mirrors that timestamp
  // so every case can hand in a clock it knows is past the cooldown.
  let saidAt = 0
  const say = (data, later) => {
    const minutes = rateLimitNoticeMinutes(data, saidAt + later)
    if (minutes != null) saidAt += later
    return minutes
  }

  it('reports the minutes Spotify asked for', () => {
    expect(say(limited(240), AFTER)).toBe(240)
  })

  it('never reports a negative wait', () => {
    expect(say(limited(-1), AFTER)).toBe(0)
  })

  it('ignores summaries with no rate limit in them', () => {
    expect(
      say({ type: 'spotify_sync', changed: true, rate_limited: 0 }, MIN)
    ).toBe(null)
  })

  it('ignores every other WebSocket event', () => {
    expect(say({ status: 'done' }, MIN)).toBe(null)
  })

  it('says it once, not once per two-minute wake-up', () => {
    expect(say(limited(240), AFTER)).toBe(240)
    expect(say(limited(239), 2 * MIN)).toBe(null)
    expect(say(limited(238), 4 * MIN)).toBe(null)
  })

  it('says it again once the cooldown has passed', () => {
    say(limited(240), AFTER)
    expect(say(limited(240), AFTER + AFTER)).toBe(240)
  })
})
