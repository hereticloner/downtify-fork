import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ editCollectionItems: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: api }))

let removeCollectionItem

beforeEach(async () => {
  vi.resetModules()
  api.editCollectionItems.mockReset()
  api.editCollectionItems.mockResolvedValue({ data: { name: 'Mix' } })
  ;({ removeCollectionItem } = await import('../model/collections'))
})

describe('collection member removal', () => {
  it('removes one playlist through the existing items endpoint', async () => {
    await removeCollectionItem('Mix', 'Roadtrip')

    expect(api.editCollectionItems).toHaveBeenCalledWith('Mix', {
      add: [],
      remove: ['Roadtrip'],
    })
  })
})
