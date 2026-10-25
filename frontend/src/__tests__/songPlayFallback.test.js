import { beforeEach, describe, expect, it, vi } from 'vitest'

const state = vi.hoisted(() => ({
  playStream: vi.fn(),
  previewToggle: vi.fn(),
  actionsPlay: vi.fn(),
  findTrack: vi.fn(),
  toast: vi.fn(),
}))

vi.mock('/src/model/stream', () => ({
  isStreamingSong: () => false,
  playStream: state.playStream,
  resolvingFor: () => false,
  // The real one lives in model/stream.js; this mirrors it closely enough
  // for the queue-building case (library track when found, else a stream).
  songToPlayerTrack: (song, findTrack) => {
    const artist = (song?.artists || [])[0] || song?.artist || ''
    const title = song?.name || song?.title || ''
    const found = findTrack ? findTrack(artist, title) : null
    if (found) return found
    return {
      file: '',
      stream: true,
      video_id: '',
      title,
      artist,
      url: '',
      duration: Number(song?.duration) || 0,
    }
  },
}))

vi.mock('/src/model/streamResolve', () => ({
  MAX_STREAM_SECONDS: 600,
  rowKey: (song) => `${song.artists?.[0] || song.artist}|${song.name}`,
  songArtist: (song) => (song?.artists || [])[0] || song?.artist || '',
  songTitle: (song) => song?.name || song?.title || '',
}))

vi.mock('/src/model/library', () => ({
  useLibrary: () => ({ findTrack: state.findTrack }),
}))

vi.mock('/src/model/player', () => ({
  usePlayer: () => ({
    isPlaying: { value: false },
    resolving: { value: null },
    toggle: vi.fn(),
  }),
}))

vi.mock('/src/model/preview', () => ({
  usePreview: () => ({
    canPreview: () => true,
    activeId: { value: '' },
    isPlaying: { value: false },
    isLoading: { value: false },
    progress: { value: 0 },
    stopFor: vi.fn(),
    toggle: state.previewToggle,
  }),
}))

vi.mock('/src/model/trackActions', () => ({
  useTrackActions: () => ({ play: state.actionsPlay }),
}))

vi.mock('/src/model/ui', () => ({
  useUi: () => ({ toast: state.toast }),
}))

vi.mock('/src/i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}))

import { useSongStarter } from '../model/songPlay'

const song = (overrides = {}) => ({
  name: 'Believe',
  artists: ['Cher'],
  ...overrides,
})

describe('useSongStarter: stream first, preview fallback', () => {
  beforeEach(() => {
    state.playStream.mockReset()
    state.playStream.mockResolvedValue(true)
    state.previewToggle.mockReset()
    state.previewToggle.mockResolvedValue(true)
    state.actionsPlay.mockReset()
    state.findTrack.mockReset()
    state.findTrack.mockReturnValue(null)
    state.toast.mockReset()
  })

  it('streams a normal track instead of previewing it', async () => {
    const start = useSongStarter()
    await start(song())
    expect(state.playStream).toHaveBeenCalledOnce()
    expect(state.previewToggle).not.toHaveBeenCalled()
  })

  it('falls back to the preview clip over the stream cap', async () => {
    const start = useSongStarter()
    await start(song({ duration: 3600 }))
    expect(state.previewToggle).toHaveBeenCalledOnce()
    expect(state.playStream).not.toHaveBeenCalled()
  })

  it('falls back to the preview clip without a title to search for', async () => {
    const start = useSongStarter()
    await start(song({ name: '' }))
    expect(state.previewToggle).toHaveBeenCalledOnce()
    expect(state.playStream).not.toHaveBeenCalled()
  })

  it('plays the whole list as a mixed queue when songs are passed', async () => {
    const start = useSongStarter()
    const list = [song(), song({ name: 'Strong Enough' })]
    await start(list[1], { songs: list })
    expect(state.actionsPlay).toHaveBeenCalledOnce()
    const [tracks, at] = state.actionsPlay.mock.calls[0]
    expect(tracks).toHaveLength(2)
    expect(tracks[0]).toMatchObject({ stream: true, title: 'Believe' })
    expect(at).toBe(1)
    expect(state.playStream).not.toHaveBeenCalled()
  })

  it('prefers the library track over streaming', async () => {
    const library = { file: 'Cher - Believe.mp3', url: '/downloads/x.mp3' }
    state.findTrack.mockReturnValue(library)
    const start = useSongStarter()
    await start(song(), { queue: [library] })
    expect(state.actionsPlay).toHaveBeenCalledWith([library], 0, null)
    expect(state.playStream).not.toHaveBeenCalled()
  })
})
