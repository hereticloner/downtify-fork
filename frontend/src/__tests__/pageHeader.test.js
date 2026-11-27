import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Library index state shared by every useLibrary() caller in this file. Tests
// mutate it in place to model which albums the background lookup discovered.
const libraryMock = vi.hoisted(() => ({
  albums: { value: [] },
  albumsComplete: { value: true },
  ensureAlbums: vi.fn(() => Promise.resolve()),
}))
const testRoot = join(dirname(fileURLToPath(import.meta.url)), '..')
const readView = (name) => readFileSync(join(testRoot, 'views', name), 'utf8')

// The views below reach the API/model layer; stub the pieces they touch so
// the SSR render stays in Node without a request or a socket.
vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    onForbidden: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({
        data: { signed_in: true, user: { role: 'admin', username: 'yeet' } },
      }),
    getSettings: () => Promise.resolve({ data: {} }),
    getQueue: () => Promise.resolve({ data: [] }),
    onMessage: () => () => {},
    getStats: () =>
      Promise.resolve({
        data: {
          library: { tracks: 7, playlists: 2, likes: 1 },
          downloads: { total: 3, last_30_days: 1, per_day: [] },
          playback: {
            total: 11,
            measured: {
              seconds: 3661,
              plays: 11,
              completions: 9,
              skips: 1,
              completion_rate: 0.8181,
              skip_rate: 0.0909,
            },
            top_tracks: [
              {
                summary: 'Artist - Track',
                artist: 'Artist',
                title: 'Track',
                album: 'Album',
                count: 11,
              },
            ],
            top_contexts: [],
            recent: [
              {
                at: '2026-11-25T21:15:00+00:00',
                date: '2026-11-25',
                summary: 'Artist - Track',
                artist: 'Artist',
                title: 'Track',
                album: 'Album',
                context: '',
                context_type: '',
                source: 'spotify',
              },
            ],
            profile: {
              first_at: '2026-10-07T12:18:00+00:00',
              last_at: '2026-11-25T12:00:00Z',
              unique: { tracks: 8, artists: 4, albums: 5 },
              by_source: { downtify: 2, spotify: 7, lastfm: 2 },
              top_artists: [
                { artist: 'Artist', count: 11 },
                { artist: 'Second Artist', count: 3 },
              ],
              top_albums: [{ album: 'Album', artist: 'Artist', count: 11 }],
              weeks: [
                { start: '2026-10-31', end: '2026-11-06', count: 8 },
                { start: '2026-11-07', end: '2026-11-13', count: 6 },
                { start: '2026-11-14', end: '2026-11-20', count: 4 },
                { start: '2026-11-21', end: '2026-11-27', count: 2 },
              ],
            },
            period: {
              days: 30,
              total: 5,
              by_source: { downtify: 1, spotify: 3, lastfm: 1 },
            },
            unique: { tracks: 4, artists: 2, albums: 3 },
            track_time: {
              seconds: 3661,
              plays_with_duration: 5,
              plays_without_duration: 0,
            },
            lastfm: {
              loved_plays: 0,
              mbid_plays: 4,
              imported_plays: 3800,
              backfill: {
                done: false,
                oldest_at: '2026-10-11T21:46:08Z',
                newest_at: '2026-11-25T11:51:48Z',
              },
            },
            context_labels: {},
          },
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
    albums: libraryMock.albums,
    albumsComplete: libraryMock.albumsComplete,
    ensureAlbums: libraryMock.ensureAlbums,
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
  it('renders the signed-in listener profile masthead', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { load } = useStats()
    await load()
    const html = await render(StatsView)
    expect(html).toMatch(/<h1[^>]*text-display[^>]*>yeet<\/h1>/)
    expect(html).toContain(t('stats.profileSubtitle'))
    expect(html).toContain(t('stats.period30'))
  })

  it('splits a legacy summary-only top track in the masthead', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { stats, load } = useStats()
    await load()
    stats.value.playback.top_tracks = [
      { summary: 'Legacy Artist - Legacy Track', count: 11 },
    ]

    const html = await render(StatsView)

    expect(html).toContain('Legacy Artist')
    expect(html).toContain('Legacy Track')
    expect(html).not.toContain('Legacy Artist - Legacy Track')
  })

  it('renders lifetime profile totals and canonical source ledger', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { stats, load } = useStats()
    await load()

    const html = await render(StatsView)

    expect(stats.value.playback.total).toBe(11)
    expect(html).toMatch(/>11<\/div>/)
    expect(html).toMatch(/>4<\/div>/)
    expect(html).toMatch(/>8<\/div>/)
    expect(html).toMatch(/>5<\/div>/)
    expect(html).toContain(t('stats.totalPlays'))
    expect(html).toContain(t('stats.allTime'))
    expect(html).toContain(t('stats.sourceSpotify'))
    expect(html).toContain(t('stats.sourceLastfm'))
  })

  it('renders recent, top artists, top albums, top tracks and weekly report', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { load } = useStats()
    await load()

    const html = await render(StatsView)

    for (const key of [
      'stats.recentPlays',
      'stats.topArtists',
      'stats.topAlbums',
      'stats.topTracks',
      'stats.listeningReport',
      'stats.canonicalPlays',
      'stats.archiveScope',
      'stats.knownTrackTime',
      'stats.trackTimeHint',
      'stats.lastfmDetail',
    ]) {
      expect(html, key).toContain(t(key))
    }
    expect(html).toContain('Artist')
    expect(html).toContain('Track')
    expect(html).toContain('Album')
    expect(html).toContain(t('stats.hoursMinutes', { hours: 1, minutes: 1 }))
    expect(html).toContain(t('stats.periodSummary', { days: 30 }))
    expect(html).toContain('data-source="spotify"')
    expect(html).toMatch(/data-play-count[^>]*>11</)
  })

  it('does not render hourly patterns, heatmap or legacy dashboard panels', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { load } = useStats()
    await load()

    const html = await render(StatsView)

    for (const key of [
      'stats.patterns',
      'stats.activityHeatmap',
      'stats.downloadsPerDay',
      'stats.spotifyRecent',
      'stats.topContexts',
      'stats.trend',
    ]) {
      expect(html, key).not.toContain(t(key))
    }
    expect(html).not.toContain('data-pattern-chart')
    expect(html).not.toContain('data-heatmap')
  })

  it('renders a truthful empty profile without invented rows', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { stats, loading } = useStats()
    stats.value = {
      playback: {
        total: 0,
        top_tracks: [],
        recent: [],
        profile: {
          first_at: '',
          last_at: '',
          unique: { tracks: 0, artists: 0, albums: 0 },
          by_source: { downtify: 0, spotify: 0, lastfm: 0 },
          top_artists: [],
          top_albums: [],
          weeks: [
            { start: '2026-10-31', end: '2026-11-06', count: 0 },
            { start: '2026-11-07', end: '2026-11-13', count: 0 },
            { start: '2026-11-14', end: '2026-11-20', count: 0 },
            { start: '2026-11-21', end: '2026-11-27', count: 0 },
          ],
        },
        period: {
          days: 30,
          total: 0,
          by_source: { downtify: 0, spotify: 0, lastfm: 0 },
        },
        unique: { tracks: 0, artists: 0, albums: 0 },
        track_time: {
          seconds: 0,
          plays_with_duration: 0,
          plays_without_duration: 0,
        },
        lastfm: {
          loved_plays: 0,
          mbid_plays: 0,
          imported_plays: 0,
          backfill: { done: false, oldest_at: '', newest_at: '' },
        },
      },
    }
    loading.value = false

    const html = await render(StatsView)

    expect(html).toContain(t('stats.profileEmpty'))
    expect(html).not.toContain('undefined')
    expect(html).not.toContain('Invalid Date')
  })
})

describe('StatsView top album covers', () => {
  beforeEach(() => {
    libraryMock.albums.value = []
    libraryMock.albumsComplete.value = true
    libraryMock.ensureAlbums.mockReset()
    libraryMock.ensureAlbums.mockImplementation(() => Promise.resolve())
  })

  async function renderWith({ library = [], topAlbums = [] } = {}) {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { stats, load } = useStats()
    await load()
    libraryMock.albums.value = library
    stats.value.playback.profile.top_albums = topAlbums
    return render(StatsView)
  }

  it('renders the matching library cover with the album as alt text', async () => {
    const html = await renderWith({
      library: [
        {
          artist: 'Artist',
          title: 'Album',
          cover: '/cover?file=Artist%20-%20Album.jpg',
        },
      ],
      topAlbums: [{ album: 'Album', artist: 'Artist', count: 11 }],
    })

    expect(html).toContain('/cover?file=Artist%20-%20Album.jpg')
    expect(html).toMatch(/<img[^>]*alt="Album"/)
  })

  it('keeps the initials fallback when no library album matches', async () => {
    const html = await renderWith({
      library: [
        {
          artist: 'Other',
          title: 'Other Album',
          cover: '/cover?file=other.jpg',
        },
      ],
      topAlbums: [{ album: 'Unmatched Album', artist: 'Nobody', count: 3 }],
    })

    expect(html).not.toContain('/cover?file=')
    expect(html).toContain('>UA</span>')
  })

  it("picks each row's own cover when two artists share an album title", async () => {
    const html = await renderWith({
      library: [
        {
          artist: 'Artist One',
          title: 'Same Title',
          cover: '/cover?file=one.jpg',
        },
        {
          artist: 'Artist Two',
          title: 'Same Title',
          cover: '/cover?file=two.jpg',
        },
      ],
      topAlbums: [
        { album: 'Same Title', artist: 'Artist One', count: 4 },
        { album: 'Same Title', artist: 'Artist Two', count: 2 },
      ],
    })

    expect(html).toContain('/cover?file=one.jpg')
    expect(html).toContain('/cover?file=two.jpg')
    expect(html.indexOf('/cover?file=one.jpg')).toBeLessThan(
      html.indexOf('/cover?file=two.jpg')
    )
  })

  it('matches artist + album case-insensitively', async () => {
    const html = await renderWith({
      library: [
        { artist: 'artist', title: 'album', cover: '/cover?file=lower.jpg' },
      ],
      topAlbums: [{ album: 'ALBUM', artist: 'ARTIST', count: 5 }],
    })

    expect(html).toContain('/cover?file=lower.jpg')
  })

  it('truncates long localized album and artist names', async () => {
    const longAlbum =
      'An Extremely Long Album Title That Must Not Break The Grid'
    const longArtist = 'A Very Long Localized Artist Name With Many Words'
    const html = await renderWith({
      topAlbums: [{ album: longAlbum, artist: longArtist, count: 1 }],
    })

    expect(html).toContain(longAlbum)
    expect(html).toContain(longArtist)
    expect(html).toContain('mt-3 truncate font-bold')
    expect(html).toContain('mt-1 truncate text-[13px] text-muted')
  })

  it('guards the background album lookup against rejection', () => {
    const source = readView('StatsView.vue')

    expect(source).toMatch(/if \(!library\.albumsComplete\.value\)/)
    expect(source).toMatch(/library\.ensureAlbums\(\)\.catch\(/)
  })
})

describe('StatsView compact display scale', () => {
  it('restyles the Stats-only cover fallback to display initials', async () => {
    const StatsView = (await import('/src/views/StatsView.vue')).default
    const { stats, load } = useStats()
    await load()
    libraryMock.albums.value = []
    stats.value.playback.profile.top_albums = [
      { album: 'Unmatched Album', artist: 'Nobody', count: 3 },
    ]

    const html = await render(StatsView)

    expect(html).toContain('>UA</span>')
    // SSR escapes `&` to `&amp;` inside class attributes.
    for (const cls of [
      '_.eyebrow]:font-display',
      '_.eyebrow]:text-[24px]',
      '_.eyebrow]:font-bold',
      '_.eyebrow]:text-fg',
    ]) {
      expect(html, cls).toContain(cls)
    }
  })

  it('keeps the period total at the approved 30px role size', () => {
    const source = readView('StatsView.vue')

    expect(source).toMatch(
      /class="text-display mt-3 text-3xl leading-none font-bold tabular"[\s\S]{0,120}\{\{ number\(period\.total \?\? 0\) \}\}/
    )
  })

  it('uses the approved compact classes and drops the oversized ones', () => {
    const source = readView('StatsView.vue')

    for (const cls of [
      'sm:text-[32px]',
      'text-[28px]',
      'text-[24px]',
      'text-[20px]',
    ]) {
      expect(source, cls).toContain(cls)
    }
    // The approved 30px period total uses the `text-3xl` utility, so the
    // oversized arbitrary values must be gone from every display role.
    for (const cls of [
      'sm:text-[42px]',
      'text-[34px]',
      'text-[36px]',
      'text-[30px]',
    ]) {
      expect(source, cls).not.toContain(cls)
    }
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
