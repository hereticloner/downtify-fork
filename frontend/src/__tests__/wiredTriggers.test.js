import { describe, expect, it, vi } from 'vitest'

// The modal reaches the API model only; stub it so no request is made and
// the SSR render in Node stays quiet.
vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    searchArtistArt: () => Promise.resolve({ data: [] }),
    getSpotifyArtistArtCandidate: () => Promise.resolve({ data: {} }),
  },
}))

// `useI18n` and the dialog focus model touch a few browser globals at
// import time; a minimal shim keeps the render in Node (same approach as
// selection.test.js).
globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
}
globalThis.window = {
  location: {
    protocol: 'http:',
    host: 'localhost:8000',
    origin: 'http://localhost:8000',
  },
  matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  addEventListener: () => {},
  removeEventListener: () => {},
}
globalThis.document = {
  activeElement: null,
  documentElement: { setAttribute: () => {}, style: {} },
  createElement: () => ({ style: {} }),
  querySelector: () => null,
  addEventListener: () => {},
  removeEventListener: () => {},
}

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { setLocale } from '../i18n'
import ArtistArtModal from '../components/library/ArtistArtModal.vue'

setLocale('en')

// Dialog content lives in a <Teleport to="body">, so SSR puts it in
// `ctx.teleports` rather than the page string; join both for assertions.
async function render(component, props) {
  const app = createSSRApp({ render: () => h(component, props) })
  const ctx = {}
  const html = await renderToString(app, ctx)
  return html + Object.values(ctx.teleports || {}).join('')
}

describe('artist bio clear trigger', () => {
  it('offers Clear bio when a bio is saved', async () => {
    const html = await render(ArtistArtModal, {
      open: true,
      artistName: 'Kenji Aoki',
      initialTab: 'bio',
      bio: 'A saved biography.',
    })
    expect(html).toContain('Clear bio')
    expect(html).toContain('Kenji Aoki')
  })

  it('hides it when there is nothing to clear', async () => {
    const html = await render(ArtistArtModal, {
      open: true,
      artistName: 'Kenji Aoki',
      initialTab: 'bio',
      bio: '',
    })
    expect(html).not.toContain('Clear bio')
  })
})
