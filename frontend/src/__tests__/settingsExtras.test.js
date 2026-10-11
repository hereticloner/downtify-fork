import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  onUnauthorized: () => () => {},
  getAuthStatus: () =>
    Promise.resolve({
      data: { signed_in: true, user: { role: 'admin', username: 'me' } },
    }),
  getSettings: () => Promise.resolve({ data: {} }),
  setSettings: vi.fn(() => Promise.resolve({ data: {} })),
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

import { useSettingsManager } from '../model/settings'

beforeEach(() => {
  api.setSettings.mockClear()
  api.setSettings.mockResolvedValue({ data: {} })
})

describe('hidden server settings are wired', () => {
  it('exposes the Navidrome extras and the mini player flag', () => {
    const { settings } = useSettingsManager()
    expect(settings.value.navidrome.scan_after_download).toBe(true)
    expect(settings.value.navidrome.client_name).toBe('Downtify')
    expect(settings.value.mini_player_enabled).toBe(true)
  })

  it('sends them when the settings form is saved', async () => {
    const { settings, saveSettings } = useSettingsManager()
    settings.value.navidrome.scan_after_download = false
    settings.value.navidrome.client_name = 'Downtify test'
    settings.value.mini_player_enabled = false

    await saveSettings()

    const payload = api.setSettings.mock.calls.at(-1)[0]
    expect(payload.navidrome.scan_after_download).toBe(false)
    expect(payload.navidrome.client_name).toBe('Downtify test')
    expect(payload.mini_player_enabled).toBe(false)
  })
})
