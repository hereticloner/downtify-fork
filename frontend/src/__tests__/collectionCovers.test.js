import { describe, expect, it } from 'vitest'
import { MAX_MOSAIC, collectionCovers, mosaicGrid } from '../lib/mosaic.js'

const playlist = (name, cover = '', covers = []) => ({ name, cover, covers })

describe('collectionCovers', () => {
  it('shows one cover per member playlist', () => {
    const playlists = [
      playlist('One', '/playlist-cover?file=one.jpg'),
      playlist('Two', '/playlist-cover?file=two.jpg'),
    ]
    expect(collectionCovers(['One', 'Two'], playlists)).toEqual([
      '/playlist-cover?file=one.jpg',
      '/playlist-cover?file=two.jpg',
    ])
  })

  it("falls back to a member's first track cover", () => {
    const playlists = [playlist('One', '', ['/cover?file=a.mp3'])]
    expect(collectionCovers(['One'], playlists)).toEqual(['/cover?file=a.mp3'])
  })

  it('caps the mosaic at nine covers', () => {
    const names = Array.from({ length: 12 }, (_, i) => `P${i}`)
    const playlists = names.map((name) => playlist(name, `/c/${name}.jpg`))
    expect(collectionCovers(names, playlists)).toHaveLength(MAX_MOSAIC)
    expect(MAX_MOSAIC).toBe(9)
  })

  it('skips unknown members and duplicate covers', () => {
    const playlists = [playlist('One', '', ['/c/one.jpg'])]
    expect(collectionCovers(['One', 'One', 'Missing'], playlists)).toEqual([
      '/c/one.jpg',
    ])
  })

  it('is empty when there is nothing to show', () => {
    expect(collectionCovers([], [])).toEqual([])
    expect(collectionCovers(['Missing'], [])).toEqual([])
    expect(collectionCovers(['One'], [playlist('One')])).toEqual([])
  })
})

describe('mosaicGrid', () => {
  it('shapes the grid by cover count', () => {
    expect(mosaicGrid(1)).toEqual({ columns: 1, rows: 1 })
    expect(mosaicGrid(2)).toEqual({ columns: 2, rows: 1 })
    expect(mosaicGrid(4)).toEqual({ columns: 2, rows: 2 })
    expect(mosaicGrid(9)).toEqual({ columns: 3, rows: 3 })
  })

  it('caps oversized mosaics at three by three', () => {
    expect(mosaicGrid(16)).toEqual({ columns: 3, rows: 3 })
    expect(mosaicGrid(0)).toEqual({ columns: 1, rows: 1 })
  })
})
