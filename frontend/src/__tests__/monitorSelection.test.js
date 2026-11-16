import { describe, expect, it } from 'vitest'
import {
  clearSelection,
  pruneSelection,
  selectMany,
  selectRange,
  selectedItems,
  toggleId,
} from '../lib/monitorSelection.js'

describe('monitor selection', () => {
  it('toggles an id without mutating the original set', () => {
    const a = new Set([1])
    const b = toggleId(a, 2)
    expect([...a]).toEqual([1])
    expect([...b]).toEqual([1, 2])
    expect([...toggleId(b, 1)]).toEqual([2])
  })

  it('adds many and clears', () => {
    expect([...selectMany(new Set([1]), [2, 3, 2])]).toEqual([1, 2, 3])
    expect([...clearSelection()]).toEqual([])
  })

  it('prunes ids that no longer exist', () => {
    expect([...pruneSelection(new Set([1, 2, 9]), [1, 2])]).toEqual([1, 2])
  })

  it('extends a shift range in visible order', () => {
    const ids = [10, 20, 30, 40]
    expect([...selectRange(new Set([10]), ids, 10, 30)]).toEqual([10, 20, 30])
    expect([...selectRange(new Set([40]), ids, 40, 20)]).toEqual([40, 30, 20])
  })

  it('falls back to a single id when the anchor is not visible', () => {
    expect([...selectRange(new Set(), [1, 2], 99, 2)]).toEqual([2])
  })

  it('resolves selected items in table order', () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 3 }]
    expect(selectedItems(items, new Set([3, 1]))).toEqual([items[0], items[2]])
  })
})
