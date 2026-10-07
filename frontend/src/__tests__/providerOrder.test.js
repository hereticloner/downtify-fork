import { describe, expect, it } from 'vitest'
import {
  dropProvider,
  moveProvider,
  providerRows,
  toggleProvider,
} from '../lib/providerOrder.js'

const ALL = ['youtube-music', 'youtube']

describe('providerRows', () => {
  it('numbers the enabled ones and parks the rest', () => {
    expect(providerRows(ALL, ['youtube-music'])).toEqual([
      { id: 'youtube-music', enabled: true, position: 1 },
      { id: 'youtube', enabled: false, position: 0 },
    ])
    expect(providerRows(ALL, ALL)).toEqual([
      { id: 'youtube-music', enabled: true, position: 1 },
      { id: 'youtube', enabled: true, position: 2 },
    ])
  })

  it('merges in the labels and ignores unknown ids', () => {
    const rows = providerRows(['a'], ['a', 'gone'], { a: { title: 'A' } })
    expect(rows).toEqual([{ id: 'a', enabled: true, position: 1, title: 'A' }])
  })
})

describe('toggleProvider', () => {
  it('appends when switched on', () => {
    expect(toggleProvider(['youtube'], 'youtube-music', true)).toEqual([
      'youtube',
      'youtube-music',
    ])
  })

  it('can put one first instead', () => {
    expect(
      toggleProvider(['youtube'], 'youtube-music', true, { first: true })
    ).toEqual(['youtube-music', 'youtube'])
  })

  it('removes when switched off', () => {
    expect(toggleProvider(ALL, 'youtube-music', false)).toEqual(['youtube'])
  })

  it('refuses to leave the list empty unless allowed', () => {
    expect(toggleProvider(['youtube'], 'youtube', false)).toBeNull()
    expect(
      toggleProvider(['youtube'], 'youtube', false, { allowEmpty: true })
    ).toEqual([])
  })

  it('ignores switching on something already on', () => {
    expect(toggleProvider(['youtube'], 'youtube', true)).toBeNull()
  })
})

describe('moveProvider', () => {
  it('swaps with the neighbour', () => {
    expect(moveProvider(ALL, 'youtube', -1)).toEqual([
      'youtube',
      'youtube-music',
    ])
    expect(
      moveProvider(['youtube', 'youtube-music'], 'youtube-music', -1)
    ).toEqual(['youtube-music', 'youtube'])
  })

  it('stops at the ends and ignores unknown ids', () => {
    expect(moveProvider(ALL, 'youtube-music', -1)).toBeNull()
    expect(moveProvider(ALL, 'youtube', 1)).toBeNull()
    expect(moveProvider(ALL, 'nope', 1)).toBeNull()
  })
})

describe('dropProvider', () => {
  it('moves a provider to another one’s slot', () => {
    expect(dropProvider(ALL, 'youtube', 'youtube-music')).toEqual([
      'youtube',
      'youtube-music',
    ])
    expect(
      dropProvider(['youtube', 'youtube-music'], 'youtube-music', 'youtube')
    ).toEqual(['youtube-music', 'youtube'])
  })

  it('ignores a drop on itself or on a disabled provider', () => {
    expect(dropProvider(ALL, 'youtube', 'youtube')).toBeNull()
    expect(dropProvider(['youtube'], 'youtube-music', 'youtube')).toBeNull()
  })
})
