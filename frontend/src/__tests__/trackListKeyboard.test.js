import { beforeEach, describe, expect, it, vi } from 'vitest'

// TrackList reaches the shared track/playlist actions and the API model (via
// LikeButton); stub them so no real network/socket is touched, same as
// selection.test.js.
const { actions, playlistActions } = vi.hoisted(() => ({
  actions: {
    play: vi.fn(),
    enqueue: vi.fn(),
    menuFor: vi.fn(() => []),
  },
  playlistActions: {
    addMenuItems: vi.fn(() => []),
  },
}))

vi.mock('/src/model/trackActions', () => ({
  useTrackActions: () => actions,
}))
vi.mock('/src/model/playlistActions', () => ({
  usePlaylistActions: () => playlistActions,
}))
vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({ data: { signed_in: true, user: { role: 'admin' } } }),
    onMessage: () => () => {},
    getSettings: () => Promise.resolve({ data: {} }),
    getTrackPalette: () => Promise.resolve({ data: {} }),
  },
}))

// TrackList reaches the real player/i18n models, which read a few browser
// globals at import time. A minimal shim keeps the SSR render in Node —
// same approach as selection.test.js (no jsdom/happy-dom dependency).
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
  scrollY: 0,
  addEventListener: () => {},
  removeEventListener: () => {},
}
globalThis.document = {
  documentElement: { setAttribute: () => {} },
  createElement: () => ({ style: {} }),
}

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { useRovingFocus } from '../model/rovingFocus'

function keyEvent(key, extra = {}) {
  return {
    key,
    shiftKey: false,
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
    ...extra,
  }
}

function setup({ count = 3 } = {}) {
  const onActivate = vi.fn()
  const onMenu = vi.fn()
  const onFocus = vi.fn()
  const roving = useRovingFocus({
    count: () => count,
    onActivate,
    onMenu,
    onFocus,
  })
  return { roving, onActivate, onMenu, onFocus }
}

describe('useRovingFocus', () => {
  it('keeps a single tab stop on the active row', () => {
    const { roving } = setup({ count: 3 })
    expect(roving.tabindexFor(0)).toBe(0)
    expect(roving.tabindexFor(1)).toBe(-1)
    expect(roving.tabindexFor(2)).toBe(-1)
  })

  it('moves the tab stop with the arrow keys and focuses the new row', () => {
    const { roving, onFocus } = setup({ count: 3 })
    const down = keyEvent('ArrowDown')
    expect(roving.onRowKeydown(down, 0)).toBe(true)
    expect(roving.active.value).toBe(1)
    expect(roving.tabindexFor(1)).toBe(0)
    expect(onFocus).toHaveBeenLastCalledWith(1)

    const up = keyEvent('ArrowUp')
    roving.onRowKeydown(up, 1)
    expect(roving.active.value).toBe(0)
  })

  it('clamps at the ends instead of wrapping', () => {
    const { roving } = setup({ count: 3 })
    roving.onRowKeydown(keyEvent('ArrowUp'), 0)
    expect(roving.active.value).toBe(0)
    roving.onRowKeydown(keyEvent('ArrowDown'), 0)
    roving.onRowKeydown(keyEvent('ArrowDown'), 1)
    roving.onRowKeydown(keyEvent('ArrowDown'), 2)
    expect(roving.active.value).toBe(2)
  })

  it('jumps to the first and last row with Home / End', () => {
    const { roving } = setup({ count: 3 })
    roving.onRowKeydown(keyEvent('End'), 0)
    expect(roving.active.value).toBe(2)
    roving.onRowKeydown(keyEvent('Home'), 2)
    expect(roving.active.value).toBe(0)
  })

  it('plays the focused row on Enter and Space', () => {
    const { roving, onActivate } = setup({ count: 3 })
    roving.onRowKeydown(keyEvent('Enter'), 2)
    expect(onActivate).toHaveBeenLastCalledWith(2)
    roving.onRowKeydown(keyEvent(' '), 1)
    expect(onActivate).toHaveBeenLastCalledWith(1)
  })

  it('opens the row menu with the Context Menu key and Shift+F10', () => {
    const { roving, onMenu } = setup({ count: 3 })
    const ctx = keyEvent('ContextMenu')
    roving.onRowKeydown(ctx, 1)
    expect(onMenu).toHaveBeenCalledWith(1, ctx)

    const f10 = keyEvent('F10', { shiftKey: true })
    roving.onRowKeydown(f10, 2)
    expect(onMenu).toHaveBeenCalledWith(2, f10)
  })

  it('prevents the browser and global shortcut handlers from also acting', () => {
    const { roving } = setup({ count: 3 })
    const event = keyEvent('ArrowDown')
    roving.onRowKeydown(event, 0)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(event.stopPropagation).toHaveBeenCalled()
  })

  it('ignores keys it does not own', () => {
    const { roving } = setup({ count: 3 })
    const event = keyEvent('a')
    expect(roving.onRowKeydown(event, 0)).toBe(false)
    expect(event.preventDefault).not.toHaveBeenCalled()
    expect(roving.active.value).toBe(0)
  })

  it('leaves keys pressed on a row control to that control', () => {
    const { roving, onActivate } = setup({ count: 3 })
    const event = keyEvent('Enter', {
      target: { tagName: 'BUTTON' },
      currentTarget: { role: 'row' },
    })
    expect(roving.onRowKeydown(event, 0)).toBe(false)
    expect(onActivate).not.toHaveBeenCalled()
    expect(event.preventDefault).not.toHaveBeenCalled()
  })

  it('does nothing on an empty list', () => {
    const { roving } = setup({ count: 0 })
    roving.setActive(4)
    expect(roving.active.value).toBe(0)
    expect(roving.tabindexFor(0)).toBe(-1)
  })
})

const LIST = [
  { file: 'a.mp3', title: 'A', artist: 'X', album: '', format: 'MP3' },
  { file: 'b.mp3', title: 'B', artist: 'Y', album: '', format: 'MP3' },
  { file: 'c.mp3', title: 'C', artist: 'Z', album: '', format: 'MP3' },
]

async function render(component, props) {
  const app = createSSRApp({ render: () => h(component, props) })
  app.component('RouterLink', {
    props: { to: { type: [String, Object], default: null } },
    setup(_, { slots }) {
      return () => h('a', {}, slots.default ? slots.default() : [])
    },
  })
  return renderToString(app)
}

describe('TrackList keyboard rendering', () => {
  const baseProps = {
    tracks: LIST,
    showAlbum: false,
    showAdded: false,
    showCover: false,
    linkArtist: false,
  }

  it('makes exactly one row the tab stop (roving tabindex)', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, baseProps)
    const stops = (html.match(/tabindex="0"/g) || []).length
    const skipped = (html.match(/tabindex="-1"/g) || []).length
    expect(stops).toBe(1)
    expect(skipped).toBe(LIST.length - 1)
  })

  it('gives every row a focus ring and an accessible name for its menu', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, baseProps)
    expect(html).toContain('focus-visible:outline-accent')
    expect(html).toContain('aria-label="More actions for A"')
  })

  it('reveals the play control on keyboard focus, not only hover', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, baseProps)
    expect(html).toContain('group-focus-within:block')
  })

  it('marks a row selected only when selection is bound', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const plain = await render(TrackList, baseProps)
    expect(plain).not.toContain('aria-selected')

    const bound = await render(TrackList, {
      ...baseProps,
      selected: new Set(['a.mp3']),
    })
    expect(bound).toContain('aria-selected="true"')
    expect(bound).toContain('aria-selected="false"')
  })

  it('exposes a localized keyboard hint to screen readers', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, baseProps)
    expect(html).toMatch(/aria-describedby="[^"]+"/)
    expect(html).toContain('Use the arrow keys to move between songs')
  })
})

beforeEach(() => {
  vi.clearAllMocks()
})
