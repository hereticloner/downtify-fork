import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  onUnauthorized: () => () => {},
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
import { useSpotifySync } from '../model/spotifySync'

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
