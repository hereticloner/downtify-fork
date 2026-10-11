// Pure helpers for the manual "write the M3U now" action.
// The backend (`downtify/m3u.py`) reads `filename`, `title`, `artist`
// and `duration` from each entry.

/**
 * Turn library tracks into the entry shape the M3U endpoint wants.
 * Tracks with no file on disk are dropped.
 */
export function m3uEntries(tracks = []) {
  return (Array.isArray(tracks) ? tracks : [])
    .filter((track) => track?.file)
    .map((track) => ({
      filename: String(track.file),
      title: String(track.title || ''),
      artist: String(track.artist || ''),
      duration: Number(track.duration) || 0,
    }))
}
