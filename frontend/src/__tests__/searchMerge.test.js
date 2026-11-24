import { describe, expect, it } from 'vitest'
import { mergeSearchResults } from '../lib/searchMerge'

describe('merged library and remote search', () => {
  it('marks a remote result already in the library', () => {
    const result = mergeSearchResults(
      [{ file: 'A - One.mp3', artist: 'A', title: 'One' }],
      [{ name: 'One', artists: ['A'] }]
    )

    expect(result.tracks).toHaveLength(1)
    expect(result.tracks[0].inLibrary).toBe(true)
    expect(result.localKeys).toContain('a|one')
  })

  it('leaves a different recording alone', () => {
    const result = mergeSearchResults(
      [{ file: 'A - One.mp3', artist: 'A', title: 'One' }],
      [{ name: 'One (Live)', artists: ['A'] }]
    )

    expect(result.tracks[0].inLibrary).toBe(false)
  })
})
