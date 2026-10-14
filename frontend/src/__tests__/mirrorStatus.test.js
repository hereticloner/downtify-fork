import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  onUnauthorized: () => () => {},
  onForbidden: () => () => {},
  getAuthStatus: () =>
    Promise.resolve({
      data: { signed_in: true, user: { role: 'admin', username: 'me' } },
    }),
  getMe: () => Promise.resolve({ data: {} }),
  getSettings: () => Promise.resolve({ data: {} }),
  setSettings: () => Promise.resolve({ data: {} }),
  getSpotifySync: () => Promise.resolve({ data: { enabled: false } }),
  check_for_update: () => Promise.resolve({ data: null }),
  getMirrorStatus: vi.fn(),
  spotifyMirrorDevices: () => Promise.resolve({ data: { devices: [] } }),
  onMessage: () => () => {},
  ws_onmessage: () => {},
  ws_onerror: () => {},
  getVersion: () => Promise.resolve({ data: { version: '3.4.0' } }),
}))

vi.mock('/src/model/api', () => ({ default: api }))

// The view asks the router which section is open; without one it reads
// nothing, so `spotify` is stubbed in directly.
vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { section: 'spotify' },
    query: {},
    name: 'Settings',
  }),
  useRouter: () => ({ push: () => {}, replace: () => {} }),
  onBeforeRouteLeave: () => {},
  RouterLink: {
    props: ['to'],
    template: '<a><slot /></a>',
  },
}))

// i18n reads localStorage at import time; the theme and the diff models
// read a few browser globals. A minimal shim keeps the SSR render in Node.
globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
}
globalThis.window = {
  location: {
    origin: 'http://localhost:8000',
    protocol: 'http:',
    host: 'localhost:8000',
  },
  matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  innerWidth: 1200,
  innerHeight: 900,
  addEventListener: () => {},
  removeEventListener: () => {},
}
globalThis.document = {
  documentElement: { setAttribute: () => {}, style: {} },
  createElement: () => ({ style: {} }),
  querySelector: () => null,
  addEventListener: () => {},
  removeEventListener: () => {},
}

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

import { useMirrorStatus } from '/src/model/spotifyMirror'
import { useSettingsManager } from '/src/model/settings'
import { useAuth } from '/src/model/auth'
import { t } from '/src/i18n'

// The whole view: it renders every section's shell and the one the route
// asked for.
async function render() {
  const SettingsView = (await import('/src/views/SettingsView.vue')).default
  const app = createSSRApp({ render: () => h(SettingsView) })
  return renderToString(app)
}

// SSR never runs onMounted, so the settings store has to be filled before
// the view renders or it shows its skeletons instead. It fills itself once
// the viewer is known to be an admin.
async function renderSpotifySection() {
  await useAuth().load()
  await vi.waitFor(() => {
    expect(useSettingsManager().loaded.value).toBe(true)
  })
  return render()
}

const MIRRORS = {
  '1:kitchen': {
    uri: 'spotify:track:4uLU6hMCjMI75M1A2tKUQC',
    at: 1_760_000_000,
  },
  '1:study': { uri: 'spotify:track:0VjIjW4GlUZAMYd2vXMi3b', at: 1_760_000_900 },
}

beforeEach(() => {
  api.getMirrorStatus.mockReset()
})

describe('the Spotify Mirror status panel', () => {
  // The "why didn't this track show up on Spotify?" answer, in the one
  // place an admin already goes for it.
  it('shows the device, its state and the token', async () => {
    api.getMirrorStatus.mockResolvedValue({
      data: {
        ok: true,
        device_id: 'a1b2c3d4e5f6a7b8',
        device_name: 'Downtify Mirror',
        device_online: true,
        token_valid: true,
        last_mirrors: MIRRORS,
        last_errors: {},
      },
    })
    await useMirrorStatus().load()

    const html = await renderSpotifySection()
    expect(html).toContain(t('settings.mirrorStatus'))
    expect(html).toContain(t('settings.mirrorDevice'))
    expect(html).toContain('Downtify Mirror (a1b2c3d4…)')
    expect(html).toContain(t('settings.mirrorOnline'))
    expect(html).not.toContain(t('settings.mirrorOffline'))
    expect(html).toContain(t('settings.mirrorTokenOk'))
    expect(html).not.toContain(t('settings.mirrorTokenBad'))
  })

  // Offline is the case worth reading at a glance: the token is fine and
  // the server simply has no device to play on.
  it('says so when the device is offline', async () => {
    api.getMirrorStatus.mockResolvedValue({
      data: {
        ok: false,
        device_id: 'a1b2c3d4e5f6a7b8',
        device_name: 'Downtify Mirror',
        device_online: false,
        token_valid: true,
        last_mirrors: {},
        last_errors: {},
      },
    })
    await useMirrorStatus().load()

    const html = await renderSpotifySection()
    expect(html).toContain(t('settings.mirrorOffline'))
  })

  // An expired token is the one failure the admin can fix from here.
  it('marks a token that needs reconnecting', async () => {
    api.getMirrorStatus.mockResolvedValue({
      data: {
        ok: false,
        device_id: '',
        device_name: '',
        device_online: false,
        token_valid: false,
        last_mirrors: {},
        last_errors: {},
      },
    })
    await useMirrorStatus().load()

    const html = await renderSpotifySection()
    expect(html).toContain(t('settings.mirrorTokenBad'))
  })

  // The tracker keeps one entry per (user, player); the panel shows the
  // newest, which is the play the user is asking about.
  it('reports the newest mirror and the newest failure', async () => {
    api.getMirrorStatus.mockResolvedValue({
      data: {
        ok: true,
        device_id: 'a1b2c3d4e5f6a7b8',
        device_name: 'Downtify Mirror',
        device_online: true,
        token_valid: true,
        last_mirrors: MIRRORS,
        last_errors: {
          '1:study': { reason: 'Device is not active', at: 1_760_001_000 },
        },
      },
    })
    await useMirrorStatus().load()

    const html = await renderSpotifySection()
    expect(html).toContain('spotify:track:0VjIjW4GlUZAMYd2vXMi3b')
    expect(html).not.toContain('spotify:track:4uLU6hMCjMI75M1A2tKUQC')
    expect(html).toContain('Device is not active')
  })

  it('says so when nothing failed', async () => {
    api.getMirrorStatus.mockResolvedValue({
      data: {
        ok: true,
        device_id: 'a1b2c3d4e5f6a7b8',
        device_name: 'Downtify Mirror',
        device_online: true,
        token_valid: true,
        last_mirrors: MIRRORS,
        last_errors: {},
      },
    })
    await useMirrorStatus().load()

    const html = await renderSpotifySection()
    expect(html).toContain(t('settings.mirrorNone'))
  })

  // The endpoint is admin-only. A user without the right gets nothing -
  // and no error either, since the whole section is already the admin's.
  it('stays empty when the endpoint refuses the request', async () => {
    api.getMirrorStatus.mockRejectedValue(new Error('This needs an admin'))
    await useMirrorStatus().load()

    const html = await renderSpotifySection()
    expect(html).not.toContain(t('settings.mirrorStatus'))
  })
})
