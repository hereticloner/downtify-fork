// The parts of a collection that still need downloading.
//
// A collection holds library playlists; a playlist tracks its Spotify
// download as a batch that reports how many tracks are still missing
// (see `GET /api/playlists/batches`). A collection is "missing tracks"
// when at least one member playlist still has some. Pure, so the
// Collections page and its tests share one definition and no component
// is needed to exercise the selection.

function missingOf(playlist) {
  return Number(playlist?.batch?.missing_count || 0)
}

/**
 * The member playlists that still have tracks to download, in the order
 * the collection lists them. Each entry carries exactly the payload the
 * download-missing endpoint needs. Members the library doesn't know,
 * members with no Spotify batch, complete members and duplicates are
 * skipped.
 */
export function collectionMissingPlaylists(names, playlists) {
  const byName = new Map()
  for (const playlist of playlists || []) {
    const key = String(playlist?.name || '')
    if (key) byName.set(key, playlist)
  }
  const seen = new Set()
  const out = []
  for (const rawName of names || []) {
    const name = String(rawName)
    if (seen.has(name)) continue
    seen.add(name)
    const playlist = byName.get(name)
    const batch = playlist?.batch
    if (!batch || !batch.spotify_playlist_id) continue
    const missing_count = missingOf(playlist)
    if (missing_count <= 0) continue
    out.push({
      name,
      spotify_playlist_id: String(batch.spotify_playlist_id),
      playlist_url: String(batch.playlist_url || ''),
      missing_count,
    })
  }
  return out
}

/** Total tracks still missing across the collection's member playlists. */
export function collectionMissingCount(names, playlists) {
  return collectionMissingPlaylists(names, playlists).reduce(
    (sum, member) => sum + member.missing_count,
    0
  )
}
