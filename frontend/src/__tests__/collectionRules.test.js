import { beforeEach, describe, expect, it, vi } from 'vitest'

// The rule editor only talks to the API model, so one mock with the two
// endpoints the smart-collection path uses is enough.
const api = vi.hoisted(() => ({
  getCollection: vi.fn(),
  saveCollectionRules: vi.fn(),
}))

vi.mock('/src/model/api', () => ({ default: api }))

import { blankRule, cleanRule, cleanRules } from '../lib/collectionRules'
import { getCollection, saveCollectionRules } from '../model/collections'

beforeEach(() => vi.clearAllMocks())

describe('collection rule drafts', () => {
  it('blanks a row per rule type', () => {
    expect(blankRule('added')).toEqual({ type: 'added', from: '', to: '' })
    expect(blankRule('plays')).toEqual({ type: 'plays', min: '', max: '' })
    expect(blankRule('genre')).toEqual({ type: 'genre', value: '' })
  })

  it('drops incomplete rows', () => {
    expect(cleanRule({ type: 'genre', value: '   ' })).toBeNull()
    expect(cleanRule({ type: 'added', from: '', to: '' })).toBeNull()
    expect(cleanRule({ type: 'plays', min: '', max: '' })).toBeNull()
    expect(cleanRule(null)).toBeNull()
    expect(cleanRule({ type: 'bpm', value: 120 })).toBeNull()
  })

  it('keeps a complete row in the shape the API expects', () => {
    expect(cleanRule({ type: 'genre', value: ' Rock ' })).toEqual({
      type: 'genre',
      value: 'Rock',
    })
    expect(cleanRule({ type: 'plays', min: '2', max: '9' })).toEqual({
      type: 'plays',
      min: 2,
      max: 9,
    })
    expect(cleanRule({ type: 'added', from: '2024-01-01', to: '' })).toEqual({
      type: 'added',
      from: '2024-01-01',
      to: '',
    })
  })

  it('rejects a reversed play range', () => {
    expect(cleanRule({ type: 'plays', min: '9', max: '2' })).toBeNull()
  })

  it('filters a mixed draft list', () => {
    expect(
      cleanRules([
        { type: 'genre', value: 'Rock' },
        { type: 'artist', value: '' },
      ])
    ).toEqual([{ type: 'genre', value: 'Rock' }])
  })
})

describe('collections controller rules', () => {
  it('saves the rules through the API', async () => {
    api.saveCollectionRules.mockResolvedValue({ data: { name: 'Smart' } })
    expect(
      await saveCollectionRules('Smart', [{ type: 'genre', value: 'Rock' }])
    ).toEqual({ name: 'Smart' })
    expect(api.saveCollectionRules).toHaveBeenCalledWith('Smart', [
      { type: 'genre', value: 'Rock' },
    ])
  })

  it('reads a single collection', async () => {
    api.getCollection.mockResolvedValue({ data: { name: 'Smart' } })
    expect(await getCollection('Smart')).toEqual({ name: 'Smart' })
    expect(api.getCollection).toHaveBeenCalledWith('Smart')
  })
})
