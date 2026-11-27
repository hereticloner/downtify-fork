import { describe, expect, it } from 'vitest'

import { trackParts, weekLabel } from '../lib/statsProfile'

describe('trackParts', () => {
  it('prefers structured artist, title and album fields', () => {
    expect(
      trackParts({
        summary: 'Wrong - Summary',
        artist: 'Artist',
        title: 'Title',
        album: 'Album',
      })
    ).toEqual({ artist: 'Artist', title: 'Title', album: 'Album' })
  })

  it('falls back to an Artist - Title summary', () => {
    expect(trackParts({ summary: 'Artist - Title' })).toEqual({
      artist: 'Artist',
      title: 'Title',
      album: '',
    })
  })

  it('keeps a title-only summary readable', () => {
    expect(trackParts({ summary: 'Title only' })).toEqual({
      artist: '',
      title: 'Title only',
      album: '',
    })
  })

  it('returns blank fields for an empty row', () => {
    expect(trackParts({})).toEqual({ artist: '', title: '', album: '' })
  })
})

describe('weekLabel', () => {
  it('formats both UTC boundaries in the requested locale', () => {
    expect(weekLabel('2026-10-31', '2026-11-06', 'en')).toBe('Oct 31 – Nov 6')
  })

  it('returns an empty label for an invalid range', () => {
    expect(weekLabel('', '', 'en')).toBe('')
  })
})
