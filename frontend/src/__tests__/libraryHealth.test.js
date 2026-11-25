import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

const api = vi.hoisted(() => ({
  getLibraryHealth: vi.fn(),
  exportLibraryHealth: vi.fn(),
}))
const authState = vi.hoisted(() => ({ value: false }))

vi.mock('/src/model/api', () => ({ default: api }))
vi.mock('/src/model/auth', () => ({
  useAuth: () => ({ isAdmin: authState }),
}))
vi.mock('/src/i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}))

import { categoryCounts, filterFindings } from '../lib/libraryHealth'
import { exportLibraryHealth, scanLibraryHealth } from '../model/libraryHealth'

beforeEach(() => {
  vi.clearAllMocks()
  authState.value = false
})

describe('library health helpers', () => {
  it('counts every category with zero defaults', () => {
    expect(categoryCounts()).toEqual({
      missing_file: 0,
      path_mismatch: 0,
      stale_mapping: 0,
      missing_metadata: 0,
      orphan_record: 0,
    })
    expect(
      categoryCounts({
        findings: [
          { category: 'missing_file' },
          { category: 'missing_file' },
          { category: 'stale_mapping' },
        ],
      })
    ).toEqual({
      missing_file: 2,
      path_mismatch: 0,
      stale_mapping: 1,
      missing_metadata: 0,
      orphan_record: 0,
    })
  })

  it('filters findings by category and tolerates missing arrays', () => {
    const rows = [{ category: 'missing_file' }, { category: 'stale_mapping' }]
    expect(filterFindings(rows, 'all')).toBe(rows)
    expect(filterFindings(rows, 'stale_mapping')).toEqual([rows[1]])
    expect(filterFindings(undefined, 'all')).toEqual([])
  })

  it('reads and exports the health report through the API model', async () => {
    const report = { findings: [] }
    const blob = new Blob(['{}'])
    api.getLibraryHealth.mockResolvedValue({ data: report })
    api.exportLibraryHealth.mockResolvedValue({ data: blob })

    expect(await scanLibraryHealth()).toBe(report)
    expect(await exportLibraryHealth()).toBe(blob)
    expect(api.getLibraryHealth).toHaveBeenCalledWith()
    expect(api.exportLibraryHealth).toHaveBeenCalledWith({
      responseType: 'blob',
    })
  })

  it('renders the page heading and admin-only state without scanning', async () => {
    const LibraryHealthView = (await import('/src/views/LibraryHealthView.vue'))
      .default
    const app = createSSRApp({ render: () => h(LibraryHealthView) })
    app.component('RouterLink', {
      props: { to: { type: [String, Object], default: null } },
      setup(_, { slots }) {
        return () => h('a', {}, slots.default ? slots.default() : [])
      },
    })

    const html = await renderToString(app)

    expect(html).toMatch(/<h1[^>]*text-display[^>]*>/)
    expect(html).toContain('>libraryHealth.title</h1>')
    expect(html).toContain('libraryHealth.adminOnly')
    expect(api.getLibraryHealth).not.toHaveBeenCalled()
  })

  it('shows a loading state for admins before the first scan', async () => {
    authState.value = true
    const LibraryHealthView = (await import('/src/views/LibraryHealthView.vue'))
      .default
    const app = createSSRApp({ render: () => h(LibraryHealthView) })

    const html = await renderToString(app)

    expect(html).toContain('libraryHealth.loading')
    expect(html).not.toContain('libraryHealth.adminOnly')
    expect(api.getLibraryHealth).not.toHaveBeenCalled()
  })
})
