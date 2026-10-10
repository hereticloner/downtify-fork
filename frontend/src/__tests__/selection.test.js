import { beforeEach, describe, expect, it, vi } from 'vitest'

// The composable talks to the shared track/playlist actions; the render
// tests below import TrackList/SelectionBar, which use the same modules.
const { actions, playlistActions } = vi.hoisted(() => ({
  actions: {
    play: vi.fn(),
    enqueue: vi.fn(),
    downloadZip: vi.fn(async () => {}),
    remove: vi.fn(async () => []),
    menuFor: vi.fn(() => []),
  },
  playlistActions: {
    openCreate: vi.fn(),
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
// globals at import time. A minimal shim keeps the SSR render in Node.
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

import { createSSRApp, h, nextTick, ref } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { useTrackSelection } from '../model/selection'

const LIST = [
  { file: 'a.mp3', title: 'A', artist: 'X', album: '', format: 'MP3' },
  { file: 'b.mp3', title: 'B', artist: 'Y', album: '', format: 'MP3' },
  { file: 'c.mp3', title: 'C', artist: 'Z', album: '', format: 'MP3' },
]

function selection({ tracks = () => LIST, resetKey, context } = {}) {
  return useTrackSelection({ tracks, resetKey, context })
}

beforeEach(() => {
  vi.clearAllMocks()
  actions.downloadZip.mockResolvedValue(undefined)
  actions.remove.mockResolvedValue([])
})

describe('useTrackSelection', () => {
  it('starts with nothing selected', () => {
    const sel = selection()
    expect(sel.count.value).toBe(0)
    expect(sel.total.value).toBe(LIST.length)
    expect(sel.selectedTracks.value).toEqual([])
  })

  it('toggles a row in and out and tracks the count', () => {
    const sel = selection()
    sel.toggle('a.mp3')
    expect(sel.has('a.mp3')).toBe(true)
    expect(sel.count.value).toBe(1)
    sel.toggle('a.mp3')
    expect(sel.has('a.mp3')).toBe(false)
    expect(sel.count.value).toBe(0)
  })

  it('selects all, then clears with toggleAll', () => {
    const sel = selection()
    sel.selectAll()
    expect(sel.count.value).toBe(LIST.length)
    expect(sel.selectedTracks.value).toEqual(LIST)
    sel.toggleAll()
    expect(sel.count.value).toBe(0)
  })

  it('drops files that are gone', () => {
    const sel = selection()
    sel.selectAll()
    sel.drop(['a.mp3', 'c.mp3'])
    expect([...sel.selected.value]).toEqual(['b.mp3'])
    expect(sel.selectedTracks.value).toEqual([LIST[1]])
  })

  it('resets the selection when the view key changes', async () => {
    const key = ref('album:1')
    const sel = selection({ resetKey: key })
    sel.selectAll()
    expect(sel.count.value).toBe(LIST.length)
    key.value = 'album:2'
    await nextTick()
    expect(sel.count.value).toBe(0)
  })

  it('clears on demand', () => {
    const sel = selection()
    sel.selectAll()
    sel.clear()
    expect(sel.count.value).toBe(0)
  })

  it('plays the selected tracks in their list order', () => {
    const context = { type: 'album', title: 'One' }
    const sel = selection({ context: () => context })
    sel.toggle('c.mp3')
    sel.toggle('a.mp3')
    sel.playSelected()
    expect(actions.play).toHaveBeenCalledTimes(1)
    expect(actions.play).toHaveBeenCalledWith([LIST[0], LIST[2]], 0, context)
  })

  it('enqueues the selected tracks', () => {
    const sel = selection()
    sel.toggle('b.mp3')
    sel.enqueueSelected()
    expect(actions.enqueue).toHaveBeenCalledWith([LIST[1]])
  })

  it('zips the selected tracks and flags the work', async () => {
    const sel = selection()
    sel.selectAll()
    const pending = sel.zipSelected()
    expect(sel.zipping.value).toBe(true)
    await pending
    expect(actions.downloadZip).toHaveBeenCalledWith(LIST)
    expect(sel.zipping.value).toBe(false)
  })

  it('deletes the selected tracks and drops them from the selection', async () => {
    actions.remove.mockResolvedValue(['a.mp3'])
    const sel = selection()
    sel.selectAll()
    const deleted = await sel.deleteSelected()
    expect(actions.remove).toHaveBeenCalledWith(LIST)
    expect(deleted).toEqual(['a.mp3'])
    expect(sel.count.value).toBe(LIST.length - 1)
    expect(sel.has('a.mp3')).toBe(false)
  })

  it('reports deletions through onDeleted', async () => {
    actions.remove.mockResolvedValue(['b.mp3'])
    const onDeleted = vi.fn()
    const sel = useTrackSelection({ tracks: () => LIST, onDeleted })
    sel.selectAll()
    await sel.deleteSelected()
    expect(onDeleted).toHaveBeenCalledWith(['b.mp3'])
  })

  it('opens the add-to-playlist dialog with the selected tracks', () => {
    const sel = selection()
    sel.toggle('a.mp3')
    sel.addSelectedToPlaylist()
    expect(playlistActions.openCreate).toHaveBeenCalledWith([LIST[0]])
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

describe('TrackList selection rendering', () => {
  const props = {
    tracks: LIST,
    showAlbum: false,
    showAdded: false,
    showCover: false,
    linkArtist: false,
  }

  it('renders a checkbox per row plus the header select-all when bound', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, {
      ...props,
      selected: new Set(['a.mp3']),
    })
    const boxes = html.match(/role="checkbox"/g) || []
    expect(boxes).toHaveLength(LIST.length + 1)
    expect(html).toContain('aria-checked="true"')
    expect(html).toContain('aria-checked="mixed"')
  })

  it('renders no checkboxes with no selection bound', async () => {
    const TrackList = (await import('/src/components/library/TrackList.vue'))
      .default
    const html = await render(TrackList, props)
    expect(html).not.toContain('role="checkbox"')
  })
})

describe('SelectionBar', () => {
  it('shows the selected count and the bulk actions', async () => {
    const SelectionBar = (
      await import('/src/components/library/SelectionBar.vue')
    ).default
    const html = await render(SelectionBar, { count: 2, total: 5 })
    expect(html).toContain('2 selected')
    expect(html).toContain('Select all 5')
  })

  it('renders nothing when the count is zero', async () => {
    const SelectionBar = (
      await import('/src/components/library/SelectionBar.vue')
    ).default
    const html = await render(SelectionBar, { count: 0, total: 5 })
    expect(html).not.toContain('selected')
  })
})
