import { describe, expect, it, vi } from 'vitest'
import {
  filterNewSimilarSongs,
  isSimilarSongInLibrary,
} from '../lib/similarBulk'

describe('similar bulk download', () => {
  it('keeps only loaded songs missing from the library', () => {
    const songs = [
      { song_id: 'a', name: 'One' },
      { song_id: 'b', name: 'Two' },
      { song_id: 'c', name: 'Three' },
    ]
    expect(
      filterNewSimilarSongs(songs, (song) => song.song_id === 'b')
    ).toEqual([songs[0], songs[2]])
  })

  it('asks the library with separate artist and title arguments', () => {
    const hasSong = vi.fn((artist, title) => artist === 'A' && title === 'One')
    expect(
      isSimilarSongInLibrary({ name: 'One', artists: ['A'] }, { hasSong })
    ).toBe(true)
    expect(hasSong).toHaveBeenCalledWith('A', 'One')
  })

  it('returns nothing for an empty list or when all are downloaded', () => {
    expect(filterNewSimilarSongs([], () => false)).toEqual([])
    expect(filterNewSimilarSongs([{ song_id: 'a' }], () => true)).toEqual([])
  })
})
