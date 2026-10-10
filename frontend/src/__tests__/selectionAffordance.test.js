import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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
// globals at import time; a minimal shim keeps the SSR render in Node —
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
import { createLongPress } from '../model/longPress'
import { selectRowMenuItem } from '../lib/selectionMenu'
import { useTrackSelection } from '../model/selection'

const LIST = [
  { file: 'a.mp3', title: 'A', artist: 'X', album: '', format: 'MP3' },
  { file: 'b.mp3', title: 'B', artist: 'Y', album: '', format: 'MP3' },
  { file: 'c.mp3', title: 'C', artist: 'Z', album: '', format: 'MP3' },
]

const touch = (extra = {}) => ({
  pointerType: 'touch',
  clientX: 10,
  clientY: 10,
  ...extra,
})

describe('createLongPress', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('opens selection mode after the delay, with the pressed row', () => {
    const onLongPress = vi.fn()
    const press = createLongPress({ onLongPress, delay: 500 })
    press.down(touch(), 'row-1')
    vi.advanceTimersByTime(499)
    expect(onLongPress).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1)
    expect(onLongPress).toHaveBeenCalledWith('row-1')
  })

  it('reports the fired press once so the tap that ends it is swallowed', () => {
    const press = createLongPress({ onLongPress: vi.fn(), delay: 500 })
    press.down(touch())
    vi.advanceTimersByTime(500)
    expect(press.wasFired()).toBe(true)
    expect(press.consumeFired()).toBe(true)
    expect(press.consumeFired()).toBe(false)
    expect(press.wasFired()).toBe(false)
  })

  it('ignores mouse presses', () => {
    const onLongPress = vi.fn()
    const press = createLongPress({ onLongPress, delay: 500 })
    press.down(touch({ pointerType: 'mouse' }))
    vi.advanceTimersByTime(1000)
    expect(onLongPress).not.toHaveBeenCalled()
  })

  it('cancels when the finger moves past the threshold (a scroll)', () => {
    const onLongPress = vi.fn()
    const press = createLongPress({ onLongPress, delay: 500, threshold: 10 })
    press.down(touch({ clientX: 0, clientY: 0 }))
    press.move(touch({ clientX: 40, clientY: 0 }))
    vi.advanceTimersByTime(1000)
    expect(onLongPress).not.toHaveBeenCalled()
  })

  it('cancels when the press lifts early', () => {
    const onLongPress = vi.fn()
    const press = createLongPress({ onLongPress, delay: 500 })
    press.down(touch())
    press.up()
    vi.advanceTimersByTime(1000)
    expect(onLongPress).not.toHaveBeenCalled()
  })

  it('leaves a press that starts on a control to that control', () => {
    const onLongPress = vi.fn()
    const press = createLongPress({ onLongPress, delay: 500 })
    press.down(touch({ target: { closest: () => ({}) } }))
    vi.advanceTimersByTime(1000)
    expect(onLongPress).not.toHaveBeenCalled()
  })
})

describe('the row menu Select entry', () => {
  it('labels an unselected row Select and starts the selection', () => {
    const onToggle = vi.fn()
    const item = selectRowMenuItem({
      selected: false,
      selectLabel: 'Select',
      deselectLabel: 'Deselect',
      onToggle,
    })
    expect(item.label).toBe('Select')
    expect(item.icon).toBe('check')
    item.action()
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it('labels a selected row Deselect', () => {
    const item = selectRowMenuItem({
      selected: true,
      selectLabel: 'Select',
      deselectLabel: 'Deselect',
    })
    expect(item.label).toBe('Deselect')
  })

  it('drives the shared selection state when its action runs', () => {
    const sel = useTrackSelection({ tracks: () => LIST })
    const item = selectRowMenuItem({
      selected: sel.has('a.mp3'),
      selectLabel: 'Select',
      deselectLabel: 'Deselect',
      onToggle: () => sel.toggle('a.mp3'),
    })
    item.action()
    expect(sel.count.value).toBe(1)
    expect(sel.has('a.mp3')).toBe(true)
  })
})

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

// The first opening `<button …>` tag whose attributes match the predicate.
function buttonTag(html, predicate) {
  return (html.match(/<button[^>]*>/g) || []).find(predicate)
}

describe('TrackList mobile selection affordance', () => {
  const base = {
    tracks: LIST,
    showAlbum: false,
    showAdded: false,
    showCover: false,
    linkArtist: false,
  }

  it('shows a visible Select button per row before selection starts', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, { ...base, selected: new Set() })
    const select = buttonTag(
      html,
      (tag) =>
        !tag.includes('role="checkbox"') &&
        tag.includes('aria-label="Select A"')
    )
    expect(select).toBeTruthy()
    expect(select).toContain('md:hidden')
    expect(select).toContain('size-11')
  })

  it('keeps the row checkbox hidden on phones until selection mode', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, { ...base, selected: new Set() })
    const checkbox = buttonTag(
      html,
      (tag) =>
        tag.includes('role="checkbox"') && tag.includes('aria-label="Select A"')
    )
    expect(checkbox).toBeTruthy()
    expect(checkbox).toContain('max-md:hidden')
  })

  it('reveals the row checkbox on phones once selection mode is on', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, {
      ...base,
      selected: new Set(['a.mp3']),
    })
    const checkbox = buttonTag(
      html,
      (tag) =>
        tag.includes('role="checkbox"') && tag.includes('aria-label="Select A"')
    )
    expect(checkbox).toBeTruthy()
    expect(checkbox).not.toContain('max-md:hidden')
    // The visible Select button gives way to the checkbox.
    expect(
      buttonTag(
        html,
        (tag) =>
          !tag.includes('role="checkbox"') &&
          tag.includes('aria-label="Select A"')
      )
    ).toBeUndefined()
  })

  it('reserves a touch-sized leading column on phones', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, { ...base, selected: new Set() })
    expect(html).toContain('grid-cols-[44px_minmax(0,1fr)_72px]')
    const wrapper = (html.match(/<span[^>]*>/g) || []).find(
      (tag) =>
        tag.includes('max-md:min-h-11') && tag.includes('max-md:min-w-11')
    )
    expect(wrapper).toBeTruthy()
  })

  it('renders no selection controls when no selection is bound', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, base)
    expect(html).not.toContain('role="checkbox"')
    expect(html).not.toContain('aria-label="Select A"')
  })
})

describe('SelectionBar mobile position', () => {
  it('clears the mobile top bar plus the notch inset', async () => {
    const SelectionBar = (
      await import('/src/components/library/SelectionBar.vue')
    ).default
    const html = await render(SelectionBar, { count: 2, total: 5 })
    expect(html).toContain('top-[calc(4rem+env(safe-area-inset-top)+0.5rem)]')
    expect(html).toContain(
      'md:top-[calc(4.5rem+env(safe-area-inset-top)+0.5rem)]'
    )
    expect(html).not.toContain('top-[76px]')
  })
})
