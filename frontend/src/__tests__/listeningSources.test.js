import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

vi.mock('/src/model/api', () => ({
  default: {
    getStats: vi.fn(),
    onUnauthorized: () => () => {},
    onMessage: () => () => {},
  },
}))

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

import StatsView from '/src/views/StatsView.vue'
import { t } from '/src/i18n'
import { useStats } from '/src/model/stats'

async function render() {
  const { stats, loading } = useStats()
  stats.value = {
    library: { tracks: 0, playlists: 0, likes: 0 },
    downloads: { total: 0, last_30_days: 0, per_day: [] },
    playback: {
      total: 3,
      measured: {
        seconds: 0,
        plays: 0,
        completions: 0,
        skips: 0,
        completion_rate: 0,
        skip_rate: 0,
      },
      top_tracks: [],
      heatmap: [],
      streak_days: 0,
      best_day: { date: '', count: 0 },
      // A legacy payload can still carry a Spotify recent row; Stats must
      // drop it instead of presenting it as a Stats source.
      recent: [
        {
          at: '2026-11-25T20:15:00Z',
          date: '2026-11-25',
          summary: 'A - T',
          context: '',
          context_type: '',
          source: 'downtify',
        },
        {
          at: '2026-11-25T20:16:00Z',
          date: '2026-11-25',
          summary: 'B - U',
          context: '',
          context_type: '',
          source: 'spotify',
        },
        {
          at: '2026-11-25T20:17:00Z',
          date: '2026-11-25',
          summary: 'C - V',
          context: '',
          context_type: '',
          source: 'lastfm',
        },
      ],
      profile: {
        first_at: '2026-11-25T20:15:00Z',
        last_at: '2026-11-25T20:17:00Z',
        unique: { tracks: 3, artists: 3, albums: 0 },
        by_source: { downtify: 1, spotify: 0, lastfm: 2 },
        top_artists: [],
        top_albums: [],
        weeks: [],
      },
      period: {
        days: 30,
        total: 3,
        by_source: { downtify: 1, spotify: 0, lastfm: 2 },
      },
      top_contexts: [],
    },
    spotify: { recent: [], play_count: 0 },
  }
  loading.value = false
  const app = createSSRApp({ render: () => h(StatsView) })
  return renderToString(app)
}

describe('unified listening sources', () => {
  it('renders only Downtify and Last.fm rows and badges', async () => {
    const html = await render()

    expect(html).toContain('data-source="downtify"')
    expect(html).not.toContain('data-source="spotify"')
    expect(html).toContain('data-source="lastfm"')
    expect(html).toContain(t('stats.sourceDowntify'))
    expect(html).toContain(t('stats.sourceLastfm'))
    expect(html).not.toContain(t('stats.sourceSpotify'))
    expect(html).toMatch(/data-play-count[^>]*>3</)
  })
})
