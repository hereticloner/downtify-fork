import { beforeEach, describe, expect, it, vi } from 'vitest'

// The download flow only talks to the incomplete-playlist endpoint, so one
// mock with the endpoint it uses is enough.
const api = vi.hoisted(() => ({
  downloadMissingPlaylistTracks: vi.fn(),
}))

vi.mock('/src/model/api', () => ({ default: api }))

import {
  collectionMissingCount,
  collectionMissingPlaylists,
} from '../lib/collectionMissing.js'
import { downloadCollectionMissing } from '../model/collections'

const playlist = (name, batch = null) => ({ name, batch })
const batch = (id, missing) => ({
  spotify_playlist_id: id,
  playlist_url: `https://open.spotify.com/playlist/${id}`,
  missing_count: missing,
})

describe('collectionMissingPlaylists', () => {
  it('returns only the members that still have missing tracks', () => {
    const playlists = [
      playlist('Complete', batch('done', 0)),
      playlist('Needs work', batch('need', 4)),
      playlist('Untracked'),
    ]
    expect(
      collectionMissingPlaylists(
        ['Complete', 'Needs work', 'Untracked'],
        playlists
      )
    ).toEqual([
      {
        name: 'Needs work',
        spotify_playlist_id: 'need',
        playlist_url: 'https://open.spotify.com/playlist/need',
        missing_count: 4,
      },
    ])
  })

  it('keeps collection order, skipping unknown members and duplicates', () => {
    const playlists = [
      playlist('A', batch('a', 2)),
      playlist('B', batch('b', 1)),
    ]
    const names = collectionMissingPlaylists(
      ['B', 'Missing', 'A', 'A'],
      playlists
    )
    expect(names.map((member) => member.name)).toEqual(['B', 'A'])
  })

  it('is empty when nothing is missing', () => {
    expect(
      collectionMissingPlaylists(
        ['Complete'],
        [playlist('Complete', batch('done', 0))]
      )
    ).toEqual([])
    expect(collectionMissingPlaylists([], [])).toEqual([])
    expect(
      collectionMissingPlaylists(['Untracked'], [playlist('Untracked')])
    ).toEqual([])
  })

  it('sums the missing tracks across the collection', () => {
    const playlists = [
      playlist('A', batch('a', 2)),
      playlist('B', batch('b', 3)),
      playlist('C', batch('c', 0)),
    ]
    expect(collectionMissingCount(['A', 'B', 'C'], playlists)).toBe(5)
  })
})

describe('downloadCollectionMissing', () => {
  beforeEach(() => vi.clearAllMocks())

  it('queues each missing member and sums what was queued', async () => {
    api.downloadMissingPlaylistTracks
      .mockResolvedValueOnce({ data: { missing_count: 2 } })
      .mockResolvedValueOnce({ data: { count: 3 } })

    const count = await downloadCollectionMissing([
      { spotify_playlist_id: 'a', playlist_url: 'u-a' },
      { spotify_playlist_id: 'b', playlist_url: 'u-b' },
    ])

    expect(count).toBe(5)
    expect(api.downloadMissingPlaylistTracks).toHaveBeenNthCalledWith(1, {
      spotify_playlist_id: 'a',
      playlist_url: 'u-a',
    })
    expect(api.downloadMissingPlaylistTracks).toHaveBeenNthCalledWith(2, {
      spotify_playlist_id: 'b',
      playlist_url: 'u-b',
    })
  })

  it('does nothing for an empty member list', async () => {
    expect(await downloadCollectionMissing([])).toBe(0)
    expect(api.downloadMissingPlaylistTracks).not.toHaveBeenCalled()
  })
})
