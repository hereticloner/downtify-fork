import { describe, expect, it } from 'vitest'
import { artistWatchUrl, isArtistWatched } from '../lib/artistWatch'

describe('artist watch shortcut', () => {
  it('builds a Spotify artist URL only when an id exists', () => {
    expect(artistWatchUrl('123')).toBe('https://open.spotify.com/artist/123')
    expect(artistWatchUrl('')).toBe('')
  })

  it('recognizes an existing artist watch', () => {
    const items = [
      { kind: 'playlist', spotify_id: '123' },
      { kind: 'artist', spotify_id: '456' },
    ]
    expect(isArtistWatched(items, '456')).toBe(true)
    expect(isArtistWatched(items, '123')).toBe(false)
  })
})
