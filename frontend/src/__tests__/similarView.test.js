import { describe, expect, it, vi } from 'vitest'

const { getSimilarTracks, search, lookupLibrarySongs } = vi.hoisted(() => ({
  getSimilarTracks: vi.fn(),
  search: vi.fn(),
  lookupLibrarySongs: vi.fn(),
}))

vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    onForbidden: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({ data: { signed_in: true, user: { role: 'admin' } } }),
    onMessage: () => () => {},
    getSettings: () => Promise.resolve({ data: {} }),
    lookupLibrarySongs,
    search,
    getSimilarTracks,
  },
}))

vi.mock('/src/model/player', () => ({
  usePlayer: () => ({
    currentTrack: { value: null },
    isPlaying: { value: false },
    resolving: { value: null },
    enqueue: vi.fn(),
    toggle: vi.fn(),
  }),
}))

vi.mock('/src/model/trackActions', () => ({
  useTrackActions: () => ({ play: vi.fn() }),
}))

vi.mock('/src/model/ui', () => ({
  useUi: () => ({ toast: vi.fn() }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}))

// i18n reads localStorage at import time; the stream model touches the
// player. A minimal shim keeps the SSR render in Node without requests.
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
globalThis.Audio = class {
  constructor() {}
}

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import SimilarView from '/src/views/SimilarView.vue'
import { useSimilar } from '/src/model/similar'

const ROW = {
  song_id: 'v1',
  name: 'Strong Enough',
  artists: ['Cher'],
  artist: 'Cher',
  cover_url: 'https://img/v1',
  duration: 224,
  url: 'https://music.youtube.com/watch?v=v1',
  match: 0.9,
}

async function render() {
  const app = createSSRApp({ render: () => h(SimilarView) })
  app.component('RouterLink', {
    props: { to: { type: [String, Object], default: null } },
    setup(_, { slots }) {
      return () => h('a', {}, slots.default ? slots.default() : [])
    },
  })
  const ctx = {}
  const html = await renderToString(app, ctx)
  return html + Object.values(ctx.teleports || {}).join('')
}

describe('SimilarView', () => {
  it('renders the seed form and the tips before a search', async () => {
    const html = await render()
    // The seed inputs, with the locale's labels…
    expect(html).toContain('Believe')
    expect(html).toContain('Cher')
    // …and the two tip cards.
    expect(html).toContain('Start from one track')
    expect(html).not.toContain('columnheader')
  })

  it('lists the matched rows once a search lands', async () => {
    getSimilarTracks.mockResolvedValueOnce({
      data: { artist: 'Cher', track: 'Believe', tracks: [ROW] },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', 'Believe')
    const html = await render()
    // Header, one row, its wand (with an aria-label) and download flow.
    expect(html).toContain('Like “Believe” by Cher')
    expect(html).toContain('Strong Enough')
    expect(html).toContain('Find similar tracks')
    expect(html).toContain('Download Strong Enough')
    expect(html).not.toContain('Start from one track')
  })

  it('shows the empty state when nothing matches', async () => {
    getSimilarTracks.mockResolvedValueOnce({
      data: { artist: 'Cher', track: 'Believe', tracks: [] },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', 'Believe')
    const html = await render()
    expect(html).toContain('Nothing similar found')
  })
})
