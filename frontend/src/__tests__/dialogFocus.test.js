import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createDialogKeyHandler, resolveDialogKey } from '../model/dialogFocus'

function keyEvent(key, extra = {}) {
  return {
    key,
    shiftKey: false,
    altKey: false,
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
    ...extra,
  }
}

describe('resolveDialogKey', () => {
  it('closes on Escape', () => {
    expect(resolveDialogKey(keyEvent('Escape'))).toBe('close')
  })

  it('ignores keys it does not own', () => {
    expect(resolveDialogKey(keyEvent('Enter'))).toBe(null)
    expect(resolveDialogKey(keyEvent('ArrowDown'))).toBe(null)
  })

  it('wraps a forward Tab from the last focusable to the first', () => {
    expect(
      resolveDialogKey(keyEvent('Tab'), { count: 3, activeIndex: 2 })
    ).toBe('focus-first')
  })

  it('wraps Shift+Tab from the first focusable to the last', () => {
    expect(
      resolveDialogKey(keyEvent('Tab', { shiftKey: true }), {
        count: 3,
        activeIndex: 0,
      })
    ).toBe('focus-last')
  })

  it('leaves a Tab in the middle or with no focusables alone', () => {
    expect(
      resolveDialogKey(keyEvent('Tab'), { count: 3, activeIndex: 1 })
    ).toBe(null)
    expect(resolveDialogKey(keyEvent('Tab'), { count: 0 })).toBe(null)
  })
})

describe('createDialogKeyHandler', () => {
  const first = { focus: vi.fn() }
  const last = { focus: vi.fn() }

  function setup(active) {
    const onClose = vi.fn()
    const handler = createDialogKeyHandler({
      getFocusables: () => [first, last],
      onClose,
      activeElement: () => active,
    })
    return { handler, onClose }
  }

  beforeEach(() => vi.clearAllMocks())

  it('closes and swallows the event on Escape', () => {
    const { handler, onClose } = setup(last)
    const event = keyEvent('Escape')
    expect(handler(event)).toBe(true)
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(event.stopPropagation).toHaveBeenCalled()
  })

  it('cycles focus forward from the last element', () => {
    const { handler } = setup(last)
    const event = keyEvent('Tab')
    expect(handler(event)).toBe(true)
    expect(first.focus).toHaveBeenCalledTimes(1)
  })

  it('cycles focus back from the first element with Shift+Tab', () => {
    const { handler } = setup(first)
    handler(keyEvent('Tab', { shiftKey: true }))
    expect(last.focus).toHaveBeenCalledTimes(1)
  })

  it('does nothing for a Tab in the middle', () => {
    const middle = { focus: vi.fn() }
    const handler = createDialogKeyHandler({
      getFocusables: () => [first, middle, last],
      onClose: vi.fn(),
      activeElement: () => middle,
    })
    expect(handler(keyEvent('Tab'))).toBe(false)
    expect(first.focus).not.toHaveBeenCalled()
    expect(last.focus).not.toHaveBeenCalled()
  })
})
