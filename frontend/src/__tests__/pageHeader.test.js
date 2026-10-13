import { describe, expect, it, vi } from 'vitest'

// The views below reach the API/model layer; stub the pieces they touch so
// the SSR render stays in Node without a request or a socket.
vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    onForbidden: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({ data: { signed_in: true, user: { role: 'admin' } } }),
    getStats: () =>
      Promise.resolve({
        data: {
          library: { tracks: 7, playlists: 2, likes: 1 },
          downloads: { total: 3, last_30_days: 1, per_day: [] },
          playback: { total: 11, top_tracks: [] },
          spotify: {
            recent: [
              {
                played_at: '2026-10-12T21:15:00+00:00',
                artist_name: 'The Night Owls',
                track_name: 'Do I Still Recall',
                album_name: 'Night Owls',
              },
            ],
            play_count: 12,
          },
        },
      }),
  },
}))
vi.mock('/src/model/library', () => ({
  useLibrary: () => ({
    playlists: { value: [] },
    tracks: { value: [] },
    loaded: { value: false },
    loading: { value: false },
    trackCount: { value: 0 },
    load: () => {},
  }),
}))
vi.mock('/src/model/ui', () => ({
  useUi: () => ({ toast: () => {}, confirm: async () => true }),
}))

// i18n reads localStorage at import time; the diff models read a few
// browser globals. A minimal shim keeps the SSR render in Node.
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

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import PageHeader from '/src/components/library/PageHeader.vue'
import { useStats } from '/src/model/stats'
import { t } from '/src/i18n'

// Views reach `<router-link>`; a plain anchor keeps the SSR render happy.
async function render(component, props, slots) {
  const app = createSSRApp({ render: () => h(component, props, slots) })
  app.component('RouterLink', {
    props: { to: { type: [String, Object], default: null } },
    setup(_, { slots: inner }) {
      return () => h('a', {}, inner.default ? inner.default() : [])
    },
  })
  const ctx = {}
  const html = await renderToString(app, ctx)
  return html + Object.values(ctx.teleports || {}).join('')
}

describe('PageHeader', () => {
  it('renders the title as the page heading, with the house typography', async () => {
    const html = await render(PageHeader, { title: 'Library' })
    expect(html).toMatch(/<h1[^>]*text-display[^>]*>Library<\/h1>/)
  })

  it('renders an optional subtitle under the title', async () => {
    const html = await render(PageHeader, {
      title: 'Library',
      subtitle: '12 tracks',
    })
    expect(html).toContain('12 tracks')
  })

  it('omits the subtitle when there is none', async () => {
    const html = await render(PageHeader, { title: 'Library' })
    expect(html).not.toContain('mt-1.5 text-sm text-muted')
  })

  it('renders the action slot next to the title', async () => {
    const html = await render(
      PageHeader,
      { title: 'Queue' },
      { default: () => h('button', { class: 'act' }, 'Clear all') }
    )
    expect(html).toContain('flex flex-wrap items-center gap-2')
    expect(html).toContain('Clear all')
  })

  it('omits the action row when the slot is empty', async () => {
    const html = await render(PageHeader, { title: 'Queue' })
    expect(html).not.toContain('flex flex-wrap items-center gap-2')
  })
})

// The page title has to come from PageHeader (not a hand-rolled <h1>), so
// the heading carries the shared `text-display` typography and the layout
// stays consistent across views.
function expectPageHeader(html, title) {
  expect(html).toMatch(/<h1[^>]*text-display[^>]*>/)
  expect(html).toContain(`>${title}</h1>`)
}

describe('StatsView', () => {
  it('renders its title through PageHeader', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const html = await render(StatsView)
    expectPageHeader(html, t('stats.title'))
    expect(html).not.toContain('text-2xl font-semibold')
  })

  // Every panel reads `stats.library.tracks`, `stats.downloads.total` and
  // the rest, so `load` has to unwrap the Axios envelope - keeping the
  // response itself puts them all on their `?? 0` fallback and the tab
  // looks empty however full the library is.
  it('renders the numbers the stats endpoint reported', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { stats, load } = useStats()
    await load()
    expect(stats.value.library.tracks).toBe(7)
    expect(stats.value.downloads.total).toBe(3)

    // SSR never runs onMounted, so the load above is what fills the
    // store the panels read.
    const html = await render(StatsView)
    expect(html).toMatch(/>7<\/div>/)
    expect(html).toMatch(/>3<\/div>/)
    expect(html).toMatch(/>11<\/div>/)
    for (const key of [
      'stats.tracks',
      'stats.playlists',
      'stats.downloads30',
      'stats.downloadsTotal',
      'stats.plays',
      'stats.likes',
    ]) {
      expect(html, key).toContain(t(key))
    }
  })

  // The plays the Spotify history import mirrored are their own panel:
  // when did each happen, who played it, and how many are stored.
  it('renders the mirrored Spotify plays', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { load } = useStats()
    await load()

    const html = await render(StatsView)
    expect(html).toContain(t('stats.spotifyRecent'))
    expect(html).toContain('The Night Owls - Do I Still Recall')
    // The timestamp is shown as a locale date, never as the raw ISO text.
    expect(html).not.toContain('2026-10-12T21:15:00+00:00')
    expect(html).toMatch(/\w+ \d{1,2}, 2026/)
    expect(html).toContain(t('stats.spotifyPlayCount', { count: 12 }))
  })
})

describe('CollectionsView', () => {
  it('renders its title through PageHeader', async () => {
    const CollectionsView = (await import('/src/views/CollectionsView.vue'))
      .default
    const html = await render(CollectionsView)
    expectPageHeader(html, t('collections.title'))
  })
})
