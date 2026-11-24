import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({
  api: {
    search: vi.fn(),
    searchAlbums: vi.fn(),
    searchArtists: vi.fn(),
  },
  searchTracks: vi.fn(),
}))

vi.mock('/src/model/api', () => ({ default: fixture.api }))
vi.mock('/src/model/library', () => ({
  useLibrary: () => ({ searchTracks: fixture.searchTracks }),
}))
vi.mock('/src/model/account', () => ({
  useAccount: () => ({ searchAlbums: { value: true } }),
}))
vi.mock('/src/i18n', () => ({
  t: (key) => key,
  currentLocale: { value: 'en' },
}))
vi.mock('/src/lib/errors', () => ({
  friendlyError: (_t, _error, fallback) => fallback,
}))

let search

beforeEach(async () => {
  vi.resetModules()
  vi.clearAllMocks()
  fixture.searchTracks.mockResolvedValue([
    { file: 'A - One.mp3', artist: 'A', title: 'One' },
  ])
  fixture.api.search.mockResolvedValue({
    data: [{ name: 'One', artists: ['A'] }],
  })
  fixture.api.searchAlbums.mockResolvedValue({ data: [] })
  fixture.api.searchArtists.mockResolvedValue({ data: [] })
  search = (await import('../model/search')).useSearch()
})

describe('local search integration', () => {
  it('loads local tracks and marks matching remote results', async () => {
    await search.searchFor('One')

    expect(fixture.searchTracks).toHaveBeenCalledWith('One', { limit: 50 })
    expect(search.localTracks.value).toHaveLength(1)
    expect(search.songs.value[0].inLibrary).toBe(true)
  })

  it('keeps remote songs when the local request fails', async () => {
    fixture.searchTracks.mockRejectedValue(new Error('offline'))

    await search.searchFor('One')

    expect(search.localTracks.value).toEqual([])
    expect(search.songs.value).toHaveLength(1)
  })
})
