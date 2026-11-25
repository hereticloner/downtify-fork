import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

const api = vi.hoisted(() => ({
  getLyricsHealth: vi.fn(),
  fillLyricsHealth: vi.fn(),
}))
const authState = vi.hoisted(() => ({ value: false }))

vi.mock('/src/model/api', () => ({ default: api }))
vi.mock('/src/model/auth', () => ({
  useAuth: () => ({ isAdmin: authState }),
}))
vi.mock('/src/model/settings', () => ({
  useSettingsManager: () => ({
    settings: { value: { lyrics_synced_only: false } },
  }),
}))
vi.mock('/src/i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}))

import {
  chunkFiles,
  eligibleLyricsFiles,
  lyricsStatusCounts,
} from '../lib/lyricsHealth'
import { fillLyricsHealth, scanLyricsHealth } from '../model/lyricsHealth'

beforeEach(() => {
  vi.clearAllMocks()
  authState.value = false
})

describe('lyrics health helpers', () => {
  it('counts every status with zero defaults', () => {
    expect(lyricsStatusCounts()).toEqual({
      synced: 0,
      plain_only: 0,
      missing: 0,
    })
    expect(
      lyricsStatusCounts({
        findings: [
          { status: 'synced' },
          { status: 'missing' },
          { status: 'missing' },
        ],
      })
    ).toEqual({ synced: 1, plain_only: 0, missing: 2 })
  })

  it('selects missing files and plain-only files in synced-only mode', () => {
    const report = {
      findings: [
        { file: 'synced.mp3', status: 'synced' },
        { file: 'plain.mp3', status: 'plain_only' },
        { file: 'missing.mp3', status: 'missing' },
      ],
    }
    expect(eligibleLyricsFiles(report)).toEqual(['missing.mp3'])
    expect(eligibleLyricsFiles(report, true)).toEqual([
      'plain.mp3',
      'missing.mp3',
    ])
  })

  it('chunks files into bounded batches', () => {
    const files = Array.from({ length: 205 }, (_, index) => `${index}.mp3`)
    const chunks = chunkFiles(files)
    expect(chunks.map((chunk) => chunk.length)).toEqual([100, 100, 5])
    expect(chunks.flat()).toEqual(files)
    expect(chunkFiles([])).toEqual([])
  })

  it('reads and fills through the API model', async () => {
    const report = { findings: [] }
    const result = { written: 1 }
    api.getLyricsHealth.mockResolvedValue({ data: report })
    api.fillLyricsHealth.mockResolvedValue({ data: result })

    expect(await scanLyricsHealth()).toBe(report)
    expect(await fillLyricsHealth(['Song.mp3'])).toBe(result)
    expect(api.fillLyricsHealth).toHaveBeenCalledWith({
      files: ['Song.mp3'],
    })
  })

  it('renders the heading and admin-only state without scanning', async () => {
    const LyricsHealthView = (await import('/src/views/LyricsHealthView.vue'))
      .default
    const app = createSSRApp({ render: () => h(LyricsHealthView) })
    app.component('RouterLink', {
      props: { to: { type: [String, Object], default: null } },
      setup(_, { slots }) {
        return () => h('a', {}, slots.default ? slots.default() : [])
      },
    })

    const html = await renderToString(app)

    expect(html).toMatch(/<h1[^>]*text-display[^>]*>/)
    expect(html).toContain('>lyricsHealth.title</h1>')
    expect(html).toContain('lyricsHealth.adminOnly')
    expect(api.getLyricsHealth).not.toHaveBeenCalled()
  })

  it('shows a loading state for admins before the first scan', async () => {
    authState.value = true
    const LyricsHealthView = (await import('/src/views/LyricsHealthView.vue'))
      .default
    const app = createSSRApp({ render: () => h(LyricsHealthView) })

    const html = await renderToString(app)

    expect(html).toContain('lyricsHealth.loading')
    expect(html).not.toContain('lyricsHealth.adminOnly')
    expect(api.getLyricsHealth).not.toHaveBeenCalled()
  })
})
