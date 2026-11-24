export function isSimilarSongInLibrary(song, library) {
  const artist = String((song?.artists || [])[0] || song?.artist || '').trim()
  const title = String(song?.name || song?.title || '').trim()
  return !!library?.hasSong(artist, title)
}

export function filterNewSimilarSongs(songs = [], isInLibrary = () => false) {
  return (songs || []).filter((song) => !isInLibrary(song))
}
