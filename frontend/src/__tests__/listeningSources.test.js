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
      top_contexts: [],
    },
    spotify: { recent: [], play_count: 0 },
  }
  loading.value = false
  const app = createSSRApp({ render: () => h(StatsView) })
  return renderToString(app)
}

describe('unified listening sources', () => {
  it('labels each recent play with its provider', async () => {
    const html = await render()
    expect(html).toContain('data-source="downtify"')
    expect(html).toContain('data-source="spotify"')
    expect(html).toContain('data-source="lastfm"')
    expect(html).toContain('Downtify')
    expect(html).toContain('Spotify')
    expect(html).toContain('Last.fm')
    expect(html).toMatch(/data-play-count[^>]*>3</)
  })
})
