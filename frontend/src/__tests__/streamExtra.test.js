import { describe, expect, it, vi } from 'vitest'

const { search, prefetchStream } = vi.hoisted(() => ({
  search: vi.fn(),
  prefetchStream: vi.fn(),
}))

vi.mock('/src/model/api', () => ({
  default: {
    search,
    prefetchStream,
  },
}))

vi.mock('/src/model/player', () => ({
  usePlayer: () => ({
    playList: vi.fn(),
    currentTrack: { value: null },
    isPlaying: { value: false },
  }),
}))

vi.mock('/src/model/library', () => ({
  useLibrary: () => ({ findTrack: vi.fn(() => null) }),
}))

import {
  MAX_STREAM_SECONDS,
  directVideoId,
  prefetchServerCache,
  rowKey,
  songArtist,
  songTitle,
  warmServerCache,
} from '../model/streamResolve.js'
import {
  resolvingFor,
  songToPlayerTrack,
  streamTrack,
  useStream,
} from '../model/stream.js'

const SONG = {
  name: 'Believe',
  artists: ['Cher'],
  cover_url: 'https://img/xl',
}

describe('streamResolve helpers', () => {
  it('reads artist and title from either row shape', () => {
    expect(songArtist(SONG)).toBe('Cher')
    expect(songArtist({ artist: 'Cher' })).toBe('Cher')
    expect(songTitle(SONG)).toBe('Believe')
    expect(songTitle({ title: 'Believe' })).toBe('Believe')
    expect(rowKey(SONG)).toBe('cher|believe')
  })

  it('accepts only 11-character video ids', () => {
    expect(directVideoId({ youtube_id: 'dQw4w9WgXcQ' })).toBe('dQw4w9WgXcQ')
    expect(directVideoId({ song_id: 'dQw4w9WgXcQ' })).toBe('dQw4w9WgXcQ')
    expect(directVideoId({ youtube_id: 'short' })).toBe('')
    expect(directVideoId(SONG)).toBe('')
  })

  it('refuses to prefetch without a resolvable video', async () => {
    search.mockResolvedValueOnce({ data: [] })
    await expect(prefetchServerCache(SONG)).resolves.toBeUndefined()
    expect(prefetchStream).not.toHaveBeenCalled()
  })

  it('prefetches the resolved video without waiting', async () => {
    prefetchStream.mockResolvedValueOnce({ data: { queued: true } })
    await expect(
      prefetchServerCache({ ...SONG, youtube_id: 'dQw4w9WgXcQ' })
    ).resolves.toBeUndefined()
    expect(prefetchStream).toHaveBeenCalledWith('dQw4w9WgXcQ')
  })

  it('swallows a failed warm', async () => {
    prefetchStream.mockRejectedValueOnce(new Error('down'))
    await expect(warmServerCache('dQw4w9WgXcQ')).resolves.toBeUndefined()
  })

  it('keeps the same 10-minute cap as downloads', () => {
    expect(MAX_STREAM_SECONDS).toBe(600)
  })
})

describe('stream row helpers', () => {
  it('builds a transient player track', () => {
    expect(
      streamTrack(
        { ...SONG, album_name: 'Believe', duration: 224 },
        '/api/stream/file?video_id=dQw4w9WgXcQ',
        'dQw4w9WgXcQ'
      )
    ).toEqual({
      file: '',
      stream: true,
      video_id: 'dQw4w9WgXcQ',
      title: 'Believe',
      artist: 'Cher',
      album: 'Believe',
      albumArtist: 'Cher',
      cover: 'https://img/xl',
      hasCover: true,
      url: '/api/stream/file?video_id=dQw4w9WgXcQ',
      duration: 224,
    })
  })

  it('reports only the row being resolved as resolving', () => {
    const { resolvingKey } = useStream()
    expect(resolvingFor(SONG)).toBe(false)
    resolvingKey.value = rowKey(SONG)
    expect(resolvingFor(SONG)).toBe(true)
    expect(resolvingFor({ name: 'Other', artists: ['Cher'] })).toBe(false)
    resolvingKey.value = ''
  })
})

describe('songToPlayerTrack', () => {
  it('maps a downloaded song to its library track', () => {
    const found = { file: 'Cher - Believe.mp3', title: 'Believe' }
    const findTrack = (artist, title) =>
      artist === 'Cher' && title === 'Believe' ? found : null
    expect(songToPlayerTrack(SONG, findTrack)).toBe(found)
  })

  it('maps a not-downloaded song to an unresolvable-until-played stream', () => {
    expect(songToPlayerTrack(SONG, () => null)).toEqual({
      file: '',
      stream: true,
      video_id: '',
      title: 'Believe',
      artist: 'Cher',
      album: '',
      albumArtist: 'Cher',
      cover: 'https://img/xl',
      hasCover: true,
      url: '',
      duration: 0,
    })
  })

  it('keeps a known video id pinned to one version', () => {
    const track = songToPlayerTrack(
      { ...SONG, song_id: 'dQw4w9WgXcQ', duration: 224 },
      () => null
    )
    expect(track.video_id).toBe('dQw4w9WgXcQ')
    expect(track.duration).toBe(224)
  })

  it('still works without a finder (pure list mapping)', () => {
    expect(songToPlayerTrack(SONG, null)).toEqual(
      songToPlayerTrack(SONG, undefined)
    )
  })
})
