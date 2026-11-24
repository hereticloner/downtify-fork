import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  getCollectionTracks: vi.fn(),
  getCollectionAnalysis: vi.fn(),
}))

vi.mock('/src/model/api', () => ({ default: api }))

import {
  getCollectionAnalysis,
  getCollectionTracks,
} from '../model/collections'

beforeEach(() => vi.clearAllMocks())

describe('collection action data', () => {
  it('reads resolved tracks', async () => {
    api.getCollectionTracks.mockResolvedValue({
      data: { tracks: [{ song_id: 'one', name: 'One' }] },
    })
    expect(await getCollectionTracks('Mix')).toEqual({
      tracks: [{ song_id: 'one', name: 'One' }],
    })
    expect(api.getCollectionTracks).toHaveBeenCalledWith('Mix')
  })

  it('reads the analysis summary', async () => {
    const summary = {
      tracks: 1,
      duration_seconds: 123,
      bytes: 456,
      missing_tracks: 0,
      missing_ratio: 0,
    }
    api.getCollectionAnalysis.mockResolvedValue({ data: summary })
    expect(await getCollectionAnalysis('Mix')).toEqual(summary)
    expect(api.getCollectionAnalysis).toHaveBeenCalledWith('Mix')
  })
})
