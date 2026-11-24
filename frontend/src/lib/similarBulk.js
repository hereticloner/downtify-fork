export function filterNewSimilarSongs(songs = [], isInLibrary = () => false) {
  return (songs || []).filter((song) => !isInLibrary(song))
}
