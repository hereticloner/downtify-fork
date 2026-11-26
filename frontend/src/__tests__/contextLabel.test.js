import { describe, expect, it } from 'vitest'

import { t } from '/src/i18n'
import { contextLabel, spotifyContextKind } from '/src/lib/context'

describe('Spotify context labels', () => {
  it('recognizes supported URI and URL forms', () => {
    expect(spotifyContextKind('spotify:playlist:abc')).toBe('playlist')
    expect(spotifyContextKind('spotify:user:u:artist:abc')).toBe('artist')
    expect(spotifyContextKind('https://open.spotify.com/album/abc?si=x')).toBe(
      'album'
    )
    expect(spotifyContextKind('https://api.spotify.com/v1/artists/abc')).toBe(
      'artist'
    )
    expect(spotifyContextKind('Downtify Playlist')).toBe('')
  })

  it('prefers a resolved cached name', () => {
    expect(
      contextLabel(
        'spotify:playlist:abc',
        { 'spotify:playlist:abc': 'Real Playlist' },
        t
      )
    ).toBe('Real Playlist')
  })

  it('falls back to localized Spotify type labels', () => {
    expect(contextLabel('spotify:artist:abc', {}, t)).toBe(
      t('stats.contextSpotifyArtist')
    )
    expect(contextLabel('spotify:album:abc', {}, t)).toBe(
      t('stats.contextSpotifyAlbum')
    )
    expect(contextLabel('spotify:playlist:abc', {}, t)).toBe(
      t('stats.contextSpotifyPlaylist')
    )
  })

  it('keeps Downtify queue titles unchanged', () => {
    expect(contextLabel('Downtify Playlist', {}, t)).toBe('Downtify Playlist')
    expect(contextLabel('', {}, t)).toBe('')
  })
})
