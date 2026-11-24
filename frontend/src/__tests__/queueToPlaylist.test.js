import { describe, expect, it } from 'vitest'
import { queuePlaylistFiles } from '../lib/queuePlaylist'

describe('queue to playlist', () => {
  it('keeps downloaded files in queue order and skips streams', () => {
    expect(
      queuePlaylistFiles([
        { file: 'A - One.mp3' },
        { stream: true, url: 'https://example.test/expiring' },
        { file: 'B - Two.flac' },
      ])
    ).toEqual(['A - One.mp3', 'B - Two.flac'])
  })

  it('returns an empty list for an empty or stream-only queue', () => {
    expect(queuePlaylistFiles([])).toEqual([])
    expect(queuePlaylistFiles([{ stream: true }])).toEqual([])
  })
})
