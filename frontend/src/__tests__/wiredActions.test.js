import { beforeEach, describe, expect, it, vi } from 'vitest'

// Every controller module below only talks to the API model, so one mock
// with the endpoints they use is enough.
const api = vi.hoisted(() => ({
  listCollections: vi.fn(),
  createCollection: vi.fn(),
  renameCollection: vi.fn(),
  editCollectionItems: vi.fn(),
  deleteCollection: vi.fn(),
  renameDevice: vi.fn(),
  revokeDevice: vi.fn(),
  spotifyMirrorNow: vi.fn(),
  deleteArtistBio: vi.fn(),
  getIncompletePlaylists: vi.fn(),
  downloadMissingPlaylistTracks: vi.fn(),
  writePlaylistM3u: vi.fn(),
}))

vi.mock('/src/model/api', () => ({ default: api }))

import {
  createCollection,
  deleteCollection,
  editCollectionItems,
  listCollections,
  renameCollection,
} from '../model/collections'
import { renameDevice, revokeDevice } from '../model/devices'
import { mirrorNow } from '../model/spotifyMirror'
import { clearArtistBio } from '../model/artistProfile'
import {
  downloadMissingPlaylistTracks,
  loadIncompletePlaylists,
} from '../model/incompletePlaylists'
import { writePlaylistM3u } from '../model/m3u'
import { m3uEntries } from '../lib/m3u'
import { canSubmitRename } from '../lib/rename'

beforeEach(() => vi.clearAllMocks())

describe('rename dialogs', () => {
  it('only submits a changed, non-empty name', () => {
    expect(canSubmitRename('Kitchen', 'Living room')).toBe(true)
    expect(canSubmitRename('Kitchen', '  Living room  ')).toBe(true)
    expect(canSubmitRename('Kitchen', 'Kitchen')).toBe(false)
    expect(canSubmitRename('Kitchen', '   ')).toBe(false)
    expect(canSubmitRename('Kitchen', 'Other', true)).toBe(false)
  })
})

describe('collections controller', () => {
  it('lists the API collections as an array', async () => {
    api.listCollections.mockResolvedValue({ data: [{ name: 'Road trip' }] })
    expect(await listCollections()).toEqual([{ name: 'Road trip' }])
    expect(api.listCollections).toHaveBeenCalledTimes(1)
  })

  it('falls back to an empty list when the API has none', async () => {
    api.listCollections.mockResolvedValue({ data: null })
    expect(await listCollections()).toEqual([])
  })

  it('renames a collection through the POST endpoint', async () => {
    api.renameCollection.mockResolvedValue({ data: { name: 'Chill' } })
    expect(await renameCollection('Road trip', 'Chill')).toEqual({
      name: 'Chill',
    })
    expect(api.renameCollection).toHaveBeenCalledWith('Road trip', 'Chill')
  })

  it('creates, edits and deletes through the matching calls', async () => {
    api.createCollection.mockResolvedValue({ data: { name: 'A' } })
    api.editCollectionItems.mockResolvedValue({ data: { name: 'A' } })
    api.deleteCollection.mockResolvedValue({ data: { name: 'A' } })

    await createCollection('A')
    await editCollectionItems('A', { add: ['p1'], remove: ['p2'] })
    await deleteCollection('A')

    expect(api.createCollection).toHaveBeenCalledWith('A')
    expect(api.editCollectionItems).toHaveBeenCalledWith('A', {
      add: ['p1'],
      remove: ['p2'],
    })
    expect(api.deleteCollection).toHaveBeenCalledWith('A')
  })
})

describe('paired apps controller', () => {
  it('renames a device with its id and new name', async () => {
    api.renameDevice.mockResolvedValue({ data: { id: 7, name: 'Kitchen' } })
    expect(await renameDevice(7, 'Kitchen')).toEqual({ id: 7, name: 'Kitchen' })
    expect(api.renameDevice).toHaveBeenCalledWith(7, 'Kitchen')
  })

  it('unpairs a device by id', async () => {
    api.revokeDevice.mockResolvedValue({ data: { removed: true } })
    await revokeDevice(3)
    expect(api.revokeDevice).toHaveBeenCalledWith(3)
  })
})

describe('Spotify mirror controller', () => {
  it('mirrors the given track now', async () => {
    const track = { file: 'Artist/Song.mp3', title: 'Song', artist: 'Artist' }
    api.spotifyMirrorNow.mockResolvedValue({ data: { ok: true } })
    expect(await mirrorNow(track)).toEqual({ ok: true })
    expect(api.spotifyMirrorNow).toHaveBeenCalledWith(track)
  })
})

describe('artist profile controller', () => {
  it('clears only the saved bio', async () => {
    api.deleteArtistBio.mockResolvedValue({ data: { bio: '' } })
    await clearArtistBio('Kenji Aoki')
    expect(api.deleteArtistBio).toHaveBeenCalledWith('Kenji Aoki')
  })
})

describe('incomplete playlists controller', () => {
  it('returns the reports, or an empty list on a bare answer', async () => {
    api.getIncompletePlaylists.mockResolvedValue({
      data: { playlists: [{ spotify_playlist_id: 'x' }], count: 1 },
    })
    expect(await loadIncompletePlaylists()).toEqual([
      { spotify_playlist_id: 'x' },
    ])

    api.getIncompletePlaylists.mockResolvedValue({ data: {} })
    expect(await loadIncompletePlaylists()).toEqual([])
  })

  it('queues a playlist by its id and URL', async () => {
    api.downloadMissingPlaylistTracks.mockResolvedValue({
      data: { missing_count: 2 },
    })
    await downloadMissingPlaylistTracks({
      spotify_playlist_id: 'abc',
      playlist_url: 'https://open.spotify.com/playlist/abc',
    })
    expect(api.downloadMissingPlaylistTracks).toHaveBeenCalledWith({
      spotify_playlist_id: 'abc',
      playlist_url: 'https://open.spotify.com/playlist/abc',
    })
  })
})

describe('M3U entries', () => {
  it('maps library tracks to the backend entry shape', () => {
    expect(
      m3uEntries([{ file: 'a/b.mp3', title: 'B', artist: 'A', duration: 12.9 }])
    ).toEqual([
      { filename: 'a/b.mp3', title: 'B', artist: 'A', duration: 12.9 },
    ])
  })

  it('drops tracks with no file and tolerates junk', () => {
    expect(m3uEntries([{ title: 'no file' }, null])).toEqual([])
    expect(m3uEntries(undefined)).toEqual([])
  })

  it('posts the mapped entries with the playlist URL', async () => {
    api.writePlaylistM3u.mockResolvedValue({ data: { count: 1 } })
    await writePlaylistM3u('https://music.youtube.com/playlist?list=1', [
      { file: 'x.mp3', title: 'T', artist: 'A', duration: 3 },
    ])
    expect(api.writePlaylistM3u).toHaveBeenCalledWith({
      playlist_url: 'https://music.youtube.com/playlist?list=1',
      tracks: [{ filename: 'x.mp3', title: 'T', artist: 'A', duration: 3 }],
    })
  })
})
