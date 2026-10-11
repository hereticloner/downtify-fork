import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

// i18n/CoverArt/player read a few browser globals at import time; a
// minimal shim keeps the SSR render in Node (no jsdom dependency).
globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
}
globalThis.window = {
  location: {
    protocol: 'http:',
    host: 'localhost:8000',
    origin: 'http://localhost:8000',
  },
  matchMedia: () => ({ matches: false }),
  innerWidth: 1200,
  innerHeight: 900,
  addEventListener: () => {},
  removeEventListener: () => {},
}
globalThis.document = {
  documentElement: { setAttribute: () => {} },
  createElement: () => ({ style: {} }),
  querySelector: () => null,
}

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import {
  createQueueReorder,
  reorderTarget,
  resolveReorderKey,
} from '../lib/queueReorder'

function keyEvent(key, extra = {}) {
  return {
    key,
    altKey: false,
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
    ...extra,
  }
}

describe('resolveReorderKey', () => {
  it('maps Alt + arrows to a direction', () => {
    expect(resolveReorderKey(keyEvent('ArrowUp', { altKey: true }))).toBe(-1)
    expect(resolveReorderKey(keyEvent('ArrowDown', { altKey: true }))).toBe(1)
  })

  it('ignores arrows without Alt, and other keys', () => {
    expect(resolveReorderKey(keyEvent('ArrowUp'))).toBe(null)
    expect(resolveReorderKey(keyEvent('Enter', { altKey: true }))).toBe(null)
  })
})

describe('reorderTarget', () => {
  it('moves one step inside the bounds', () => {
    expect(reorderTarget(1, -1, { min: 0, max: 2 })).toBe(0)
    expect(reorderTarget(1, 1, { min: 0, max: 2 })).toBe(2)
  })

  it('returns null at either edge', () => {
    expect(reorderTarget(0, -1, { min: 0, max: 2 })).toBe(null)
    expect(reorderTarget(2, 1, { min: 0, max: 2 })).toBe(null)
  })

  it('never allows landing above the current track', () => {
    // The first queued track sits at index 3, current is 2: min = 3.
    expect(reorderTarget(3, -1, { min: 3, max: 5 })).toBe(null)
    expect(reorderTarget(4, -1, { min: 3, max: 5 })).toBe(3)
  })
})

describe('createQueueReorder', () => {
  beforeEach(() => vi.clearAllMocks())

  function setup(overrides = {}) {
    const onMove = vi.fn()
    const reorder = createQueueReorder({
      onMove,
      min: () => 0,
      max: () => 2,
      ...overrides,
    })
    return { reorder, onMove }
  }

  it('moves and reports where a row can go', () => {
    const { reorder, onMove } = setup()
    expect(reorder.canMove(1, -1)).toBe(true)
    expect(reorder.canMove(0, -1)).toBe(false)
    expect(reorder.move(1, 1)).toBe(true)
    expect(onMove).toHaveBeenCalledWith(1, 2)
  })

  it('refuses a move past the edge', () => {
    const { reorder, onMove } = setup()
    expect(reorder.move(0, -1)).toBe(false)
    expect(onMove).not.toHaveBeenCalled()
  })

  it('triggers the move from a keyboard event and owns the key', () => {
    const { reorder, onMove } = setup()
    const event = keyEvent('ArrowUp', { altKey: true })
    expect(reorder.onRowKeydown(event, 1)).toBe(true)
    expect(onMove).toHaveBeenCalledWith(1, 0)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(event.stopPropagation).toHaveBeenCalled()
  })

  it('ignores keys it does not own', () => {
    const { reorder, onMove } = setup()
    const event = keyEvent('ArrowUp')
    expect(reorder.onRowKeydown(event, 1)).toBe(false)
    expect(onMove).not.toHaveBeenCalled()
  })
})

const TRACKS = [
  {
    file: 'a.mp3',
    title: 'A',
    artist: 'X',
    album: '',
    duration: 180,
    hasCover: false,
    cover: '',
    url: '/media/a.mp3',
  },
  {
    file: 'b.mp3',
    title: 'B',
    artist: 'Y',
    album: '',
    duration: 200,
    hasCover: false,
    cover: '',
    url: '/media/b.mp3',
  },
  {
    file: 'c.mp3',
    title: 'C',
    artist: 'Z',
    album: '',
    duration: 220,
    hasCover: false,
    cover: '',
    url: '/media/c.mp3',
  },
]

function buttonTags(html, label) {
  return (html.match(/<button[^>]*>/g) || []).filter((tag) =>
    tag.includes(`aria-label="${label}"`)
  )
}

// The boolean `disabled` attribute, not the `disabled:opacity-30` class.
function isDisabled(tag) {
  return / disabled(?=[ >])/.test(tag)
}

describe('UpNextPanel reorder controls', () => {
  let html

  beforeAll(async () => {
    const { usePlayer } = await import('../model/player.js')
    // Nothing playing yet: the queue is the whole playlist, so the first
    // row can't move up past the (absent) current track.
    usePlayer().setPlaylist(TRACKS)
    const UpNextPanel = (await import('/src/components/player/UpNextPanel.vue'))
      .default
    const app = createSSRApp({ render: () => h(UpNextPanel) })
    html = await renderToString(app)
  })

  it('gives every row accessible move buttons', () => {
    expect(buttonTags(html, 'Move up')).toHaveLength(TRACKS.length)
    expect(buttonTags(html, 'Move down')).toHaveLength(TRACKS.length)
    expect(buttonTags(html, 'Remove from queue')).toHaveLength(TRACKS.length)
  })

  it('disables the edges so a track cannot leave the queue', () => {
    // The first row cannot move above the current track; the last cannot
    // move down past the end.
    expect(isDisabled(buttonTags(html, 'Move up')[0])).toBe(true)
    expect(isDisabled(buttonTags(html, 'Move up')[1])).toBe(false)
    expect(isDisabled(buttonTags(html, 'Move down').at(-1))).toBe(true)
  })

  it('describes the keyboard shortcut to screen readers', () => {
    expect(html).toMatch(/aria-describedby="reorder-hint-[^"]+"/)
    expect(html).toContain('Press Alt with the up or down arrow')
  })
})
