import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

// player.js reads localStorage at module load time (to restore the
// saved volume), which doesn't exist in Vitest's default (non-browser)
// environment — stub it before dynamically importing the module,
// rather than adding a jsdom/happy-dom dependency just for this test.
let trackInfoFromFile

beforeAll(async () => {
  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
  }
  ;({ trackInfoFromFile } = await import('../model/player.js'))
})

describe('trackInfoFromFile', () => {
  it('parses "Artist - Title" for a file at the library root', () => {
    const track = trackInfoFromFile('The Night Owls - Do I Still Recall.mp3')
    expect(track.artist).toBe('The Night Owls')
    expect(track.title).toBe('Do I Still Recall')
  })

  it('does not leak the playlist folder into the artist', () => {
    // The bug: parsing the whole path found the first " - " in
    // "My Playlist/Artist - Title.mp3" *before* the real one, so the
    // artist came out as "My Playlist/Artist" instead of "Artist".
    const track = trackInfoFromFile(
      'My Playlist/The Night Owls - Do I Still Recall.mp3'
    )
    expect(track.artist).toBe('The Night Owls')
    expect(track.title).toBe('Do I Still Recall')
  })

  it('strips a nested Artist/Album organize-by-* folder too', () => {
    const track = trackInfoFromFile(
      'The Night Owls/Some Album/The Night Owls - Do I Still Recall.mp3'
    )
    expect(track.artist).toBe('The Night Owls')
    expect(track.title).toBe('Do I Still Recall')
  })

  it('is unaffected by a folder name that itself contains " - "', () => {
    const track = trackInfoFromFile('My Playlist - 2026/Artist - Title.mp3')
    expect(track.artist).toBe('Artist')
    expect(track.title).toBe('Title')
  })

  it('only splits on the first " - ", keeping the rest in the title', () => {
    const track = trackInfoFromFile('Artist - Title - Remix.mp3')
    expect(track.artist).toBe('Artist')
    expect(track.title).toBe('Title - Remix')
  })

  it('falls back to the whole basename as the title when there is no " - "', () => {
    const track = trackInfoFromFile('My Playlist/Standalone Track.mp3')
    expect(track.artist).toBe('')
    expect(track.title).toBe('Standalone Track')
  })

  it('keeps the full relative path (with folder) in the file field', () => {
    const track = trackInfoFromFile('My Playlist/Artist - Title.mp3')
    expect(track.file).toBe('My Playlist/Artist - Title.mp3')
  })

  it('serves downloads-folder tracks from the /downloads mount', () => {
    const track = trackInfoFromFile('My Playlist/Artist - Title.mp3')
    expect(track.url).toBe('/downloads/My%20Playlist/Artist%20-%20Title.mp3')
  })

  it('serves slskd tracks left in place through /media', () => {
    const track = trackInfoFromFile('slskd/Some User/Artist - Title #1.flac')
    expect(track.url).toBe(
      '/media/slskd/Some%20User/Artist%20-%20Title%20%231.flac'
    )
  })
})

// player.js also reads `window.innerWidth` at module load time to decide
// the initial volume — each case needs a fresh module instance (isolated
// via vi.resetModules()) with its own `window`/`localStorage` stub,
// rather than the shared one `trackInfoFromFile`'s tests import once.
describe('usePlayer initial volume', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    delete globalThis.window
  })

  it('starts at max volume on a mobile-width viewport, ignoring a saved level', async () => {
    globalThis.window = { innerWidth: 375 }
    globalThis.localStorage = { getItem: () => '0.3', setItem: () => {} }
    const { usePlayer } = await import('../model/player.js')
    expect(usePlayer().volume.value).toBe(1)
  })

  it('restores the saved volume on a desktop-width viewport', async () => {
    globalThis.window = { innerWidth: 1280 }
    globalThis.localStorage = { getItem: () => '0.3', setItem: () => {} }
    const { usePlayer } = await import('../model/player.js')
    expect(usePlayer().volume.value).toBe(0.3)
  })
})

// Queue editing, driven through a fake <audio> element.
class FakeAudio {
  constructor() {
    this.src = ''
    this.currentTime = 0
    this.paused = true
    this.listeners = {}
  }
  addEventListener(name, fn) {
    this.listeners[name] = fn
  }
  play() {
    this.paused = false
    this.listeners.play?.()
    return Promise.resolve()
  }
  pause() {
    this.paused = true
    this.listeners.pause?.()
  }
  removeAttribute() {
    this.src = ''
  }
}

describe('usePlayer queue', () => {
  let player
  const titles = () => player.playlist.value.map((t) => t.title)
  const upcoming = () => player.upcoming.value.map((u) => u.track.title)

  beforeEach(async () => {
    vi.resetModules()
    globalThis.localStorage = { getItem: () => null, setItem: () => {} }
    globalThis.Audio = FakeAudio
    const { usePlayer } = await import('../model/player.js')
    player = usePlayer()
    player.setPlaylist(['A - One.mp3', 'A - Two.mp3', 'A - Three.mp3'], {
      startIndex: 0,
      context: { type: 'album', title: 'Numbers' },
    })
  })

  afterEach(() => {
    delete globalThis.Audio
  })

  it('plays from the chosen track and remembers where from', () => {
    expect(player.currentTrack.value.title).toBe('One')
    expect(player.isPlaying.value).toBe(true)
    expect(player.context.value.title).toBe('Numbers')
    expect(upcoming()).toEqual(['Two', 'Three'])
  })

  it('queues tracks next or last', () => {
    player.enqueue(['B - Last.mp3'])
    player.playNext(['B - Next.mp3'])
    expect(upcoming()).toEqual(['Next', 'Two', 'Three', 'Last'])
    expect(player.currentTrack.value.title).toBe('One')
  })

  it('reorders without losing the current track', () => {
    player.playAt(1)
    player.moveTrack(0, 2)
    expect(titles()).toEqual(['Two', 'Three', 'One'])
    expect(player.currentTrack.value.title).toBe('Two')
    expect(upcoming()).toEqual(['Three', 'One'])
  })

  it('removes an upcoming track', () => {
    player.removeAt(2)
    expect(titles()).toEqual(['One', 'Two'])
    expect(player.currentTrack.value.title).toBe('One')
  })

  it('moves on when the playing track is removed', () => {
    player.removeAt(0)
    expect(player.currentTrack.value.title).toBe('Two')
  })

  it('drops deleted files from the queue', () => {
    player.forgetFiles(['A - Two.mp3'])
    expect(titles()).toEqual(['One', 'Three'])
  })

  it('clears what is left to play', () => {
    player.clearUpcoming()
    expect(titles()).toEqual(['One'])
    expect(upcoming()).toEqual([])
  })

  it('stops after the last track unless repeating', () => {
    player.playAt(2)
    player.next()
    expect(player.isPlaying.value).toBe(false)
    player.setRepeat('all')
    player.next()
    expect(player.currentTrack.value.title).toBe('One')
  })

  it('keeps the current track first when shuffling', () => {
    player.playAt(1)
    player.setShuffle(true)
    expect(player.currentTrack.value.title).toBe('Two')
    expect(upcoming().sort()).toEqual(['One', 'Three'])
  })

  it('can stop after the current track', () => {
    player.setSleepTimer('track')
    expect(player.sleepAt.value).toBe('track')
    player.setSleepTimer(null)
    expect(player.sleepAt.value).toBe(null)
  })
})

describe('usePlayer auto-dj', () => {
  let player
  let provider

  const libraryRow = (file, artist) => ({
    file,
    url: `/downloads/${file}`,
    title: file.replace('.mp3', '').split(' - ')[1],
    artist,
  })

  beforeEach(async () => {
    vi.resetModules()
    globalThis.localStorage = { getItem: () => null, setItem: () => {} }
    globalThis.Audio = FakeAudio
    const { usePlayer } = await import('../model/player.js')
    player = usePlayer()
    provider = vi.fn(async () => [
      libraryRow('A - Encore.mp3', 'A'),
      libraryRow('B - Other.mp3', 'B'),
      libraryRow('C - Chance.mp3', 'C'),
    ])
    player.setAutoDjSource(provider)
    player.setPlaylist(['A - One.mp3'], { startIndex: 0 })
  })

  afterEach(() => {
    delete globalThis.Audio
  })

  it('keeps playing library tracks when the queue runs out', async () => {
    player.setAutoDj(true)
    await player.next()
    expect(player.isPlaying.value).toBe(true)
    // Same artist first, then everyone else (only one candidate per
    // bucket here, so the appended order is deterministic).
    const appended = player.playlist.value
      .slice(1)
      .map((t) => t.title)
    expect(appended[0]).toBe('Encore')
    expect(appended.slice(1).sort()).toEqual(['Chance', 'Other'])
    expect(provider).toHaveBeenCalledTimes(1)
  })

  it('favors the current artist first', async () => {
    player.setAutoDj(true)
    player.setAutoDjSource(async () => [
      libraryRow('B - Other.mp3', 'B'),
      libraryRow('A - Encore.mp3', 'A'),
    ])
    await player.next()
    // The queue only grows by library candidates; the current artist's
    // row must not lose its turn to a random pick.
    expect(player.currentTrack.value.artist).toBe('A')
  })

  it('adds nothing when off and stops as before', async () => {
    await player.next()
    expect(player.isPlaying.value).toBe(false)
    expect(player.playlist.value.map((t) => t.title)).toEqual(['One'])
    expect(provider).not.toHaveBeenCalled()
  })

  it('holds out tracks the queue already has', async () => {
    player.setAutoDj(true)
    player.enqueue(['A - Encore.mp3'])
    await player.next()
    // 'Encore' is already queued, so it is not offered again.
    expect(
      player.playlist.value.filter((t) => t.title === 'Encore').length
    ).toBe(1)
  })

  it('caps how many tracks it appends', async () => {
    player.setAutoDj(true)
    const library = []
    for (let i = 0; i < 40; i++) {
      library.push(libraryRow(`Artist ${i % 2} - Song ${i}.mp3`, `Artist ${i % 2}`))
    }
    player.setAutoDjSource(async () => library)
    await player.next()
    expect(player.playlist.value.length).toBe(1 + 15)
  })

  it('persists the toggle', async () => {
    const stored = []
    globalThis.localStorage = {
      getItem: () => null,
      setItem: (key, value) => stored.push([key, value]),
    }
    player.setAutoDj(true)
    expect(player.autoDj.value).toBe(true)
    expect(stored).toEqual([['downtify-player-autodj', '1']])
  })

  it('stops when the source offers nothing new', async () => {
    player.setAutoDj(true)
    player.setAutoDjSource(async () => [])
    await player.next()
    expect(player.isPlaying.value).toBe(false)
    expect(player.playlist.value.map((t) => t.title)).toEqual(['One'])
  })
})
