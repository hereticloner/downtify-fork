// Playing one song from a list of songs that may or may not be downloaded
// yet - a link's album or playlist, an artist's top songs. Once the song is
// in the library it plays through the built-in player. Until then the whole
// list goes to the player as one queue: downloaded songs play from the
// library, the rest stream in full from YouTube (see model/stream.js), so
// the player works through to the end.
//
// The fork's 30 s preview (model/preview.js) still exists and is used as a
// fallback for rows the streamer can't take - a track over the 10 minute
// stream cap, or one without an artist/title to search for. The stream path
// takes priority whenever both are available; the preview fallback is
// deliberately left in place rather than deleted.
//
// Shared by TrackDownPlay (the artist page's Top songs) and SongPlayCell
// (the number cell of the selectable lists), so both behave the same.
import { computed, onBeforeUnmount, watch } from 'vue'

import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePreview } from '/src/model/preview'
import {
  isStreamingSong,
  playStream,
  resolvingFor,
  songToPlayerTrack,
} from '/src/model/stream'
import {
  MAX_STREAM_SECONDS,
  rowKey,
  songArtist,
  songTitle,
} from '/src/model/streamResolve'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { previewKey } from '/src/lib/preview'
import { useI18n } from '/src/i18n'

/** Whether the streamer can take this song (title/artist, under the cap). */
function canStream(song) {
  if (!songArtist(song) || !songTitle(song)) return false
  return (Number(song?.duration) || 0) <= MAX_STREAM_SECONDS
}

/**
 * The preview fallback is only reached for a song the streamer declines.
 * The fork has no loguru on the frontend, so this is the console note that
 * marks the path rather than a silent disappearance of the feature.
 */
function notePreviewFallback(song) {
  if (typeof console !== 'undefined')
    console.debug('[preview] fallback (stream unavailable):', songTitle(song))
}

/**
 * `start(song, { queue, context, songs })`: make sure `song` plays - from
 * the library once it's downloaded (with `queue` after it), else as one
 * row of a mixed queue (`songs`: the whole list, downloaded or streamed)
 * the player works through to the end. What a double click on a song's row
 * does, for a caller holding the song but not its row (the Finder, starting
 * the popular track it was just asked for). Call it during setup, like any
 * composable; `start` itself can then be called any time.
 */
export function useSongStarter() {
  const { t } = useI18n()
  const library = useLibrary()
  const preview = usePreview()
  const player = usePlayer()
  const actions = useTrackActions()
  const ui = useUi()

  return function start(
    song,
    { queue = [], context = null, songs = null } = {}
  ) {
    if (Array.isArray(songs) && songs.length) {
      const key = rowKey(song)
      const at = Math.max(
        0,
        songs.findIndex((s) => s === song || rowKey(s) === key)
      )
      actions.play(
        songs.map((s) => songToPlayerTrack(s, library.findTrack)),
        at,
        context
      )
      return
    }
    const track = library.findTrack(songArtist(song), songTitle(song))
    if (track) {
      const index = (queue || []).findIndex((item) => item.file === track.file)
      if (index < 0) actions.play([track], 0, context)
      else actions.play(queue, index, context)
      return
    }
    // Stream first; the preview clip is only the fallback for tracks the
    // streamer refuses (too long, or nothing to search for).
    if (canStream(song)) {
      if (isStreamingSong(song) && player.isPlaying.value) return
      Promise.resolve(playStream(song, { context })).then((ok) => {
        if (!ok) ui.toast(t('stream.failed', { name: songTitle(song) }))
      })
      return
    }
    if (!preview.canPreview(song)) return
    notePreviewFallback(song)
    const id = previewKey(song)
    if (id && preview.activeId.value === id && preview.isPlaying.value) return
    Promise.resolve(preview.toggle(song)).then((ok) => {
      if (!ok) ui.toast(t('actions.noPreview', { name: songTitle(song) }))
    })
  }
}

/**
 * `props`: `{ song, queue, context, songs }` - the song (a search/link
 * result), the library tracks playing it starts a queue from, the
 * player's "playing from" for them, and the whole song list for a mixed
 * queue (downloaded rows from the library, the rest streamed).
 */
export function useSongPlay(props) {
  const { t } = useI18n()
  const library = useLibrary()
  const player = usePlayer()
  const preview = usePreview()
  const actions = useTrackActions()
  const ui = useUi()
  const start = useSongStarter()

  // The library track behind the song once it's downloaded - the library
  // refreshes itself shortly after a download finishes, and this follows.
  const track = computed(() =>
    library.findTrack(songArtist(props.song), songTitle(props.song))
  )
  const streaming = computed(() => isStreamingSong(props.song))
  const isCurrent = computed(
    () =>
      (!!track.value && player.currentTrack.value?.file === track.value.file) ||
      streaming.value
  )

  // The stream path wins when available; the preview fallback stays for
  // the rows it can't take.
  const streamable = computed(() => !track.value && canStream(props.song))
  const previewable = computed(
    () => !track.value && !streamable.value && preview.canPreview(props.song)
  )
  const songId = computed(() => previewKey(props.song))
  const previewActive = computed(
    () =>
      !track.value &&
      !streamable.value &&
      !!songId.value &&
      preview.activeId.value === songId.value
  )
  const previewPlaying = computed(
    () => previewActive.value && preview.isPlaying.value
  )
  const previewLoading = computed(
    () => previewActive.value && preview.isLoading.value
  )
  // Resolving the stream URL right now (direct tap, or the player working
  // through the queue): the row spins meanwhile.
  const loading = computed(
    () =>
      resolvingFor(props.song) ||
      (player.resolving.value != null &&
        rowKey(player.resolving.value) === rowKey(props.song))
  )
  // Something on this row plays: the downloaded song, its stream, or its
  // clip when the streamer won't take it.
  const playable = computed(
    () => !!track.value || streamable.value || previewable.value
  )
  const highlighted = computed(() => isCurrent.value || previewActive.value)
  const playLabel = computed(() => {
    if (isCurrent.value && player.isPlaying.value) return t('player.pause')
    if (track.value)
      return t('actions.playItem', { name: songTitle(props.song) })
    return t(
      previewPlaying.value
        ? 'actions.pausePreview'
        : previewable.value
          ? 'actions.playPreview'
          : 'actions.playItem',
      { name: songTitle(props.song) }
    )
  })

  function play() {
    if (!track.value) return
    const queue = props.queue || []
    const start = queue.findIndex((item) => item.file === track.value.file)
    if (start < 0) actions.play([track.value], 0, props.context)
    else actions.play(queue, start, props.context)
  }

  async function playPreview() {
    const ok = await preview.toggle(props.song)
    if (!ok) ui.toast(t('actions.noPreview', { name: songTitle(props.song) }))
  }

  // The play button: the song from the library; else its full stream (as
  // one row of the whole list when the caller passes it, so the player
  // works through to the end even past undownloaded rows), which the same
  // button pauses again; else the preview fallback.
  function toggle() {
    if (track.value) play()
    else if (streaming.value) player.toggle()
    else if (streamable.value)
      start(props.song, {
        queue: props.queue,
        context: props.context,
        songs: props.songs,
      })
    else if (previewable.value) playPreview()
  }

  // A double click makes sure the song plays; it never pauses a stream.
  function ensurePlaying() {
    start(props.song, {
      queue: props.queue,
      context: props.context,
      songs: props.songs,
    })
  }

  // Once the song has been downloaded the row plays the real thing, so the
  // clip ends; a row that goes away takes its clip with it.
  watch(track, (found) => {
    if (found) preview.stopFor(songId.value)
  })
  onBeforeUnmount(() => preview.stopFor(songId.value))

  return {
    track,
    isCurrent,
    loading,
    previewable,
    previewActive,
    previewPlaying,
    previewLoading,
    playable,
    highlighted,
    playLabel,
    progress: preview.progress,
    toggle,
    ensurePlaying,
  }
}
