// Mosaic covers: the grid a set of cover images fills, and the covers a
// collection takes from its member playlists. Pure, so it's unit-testable
// and shared by the CoverArt component and the Collections page.
//
// CoverArt already grids a playlist's track covers into a 2x2 tile; a
// collection sits a level above, so its mosaic comes from the playlists
// it holds (each contributing its own artwork, or its first track cover)
// and can grow to a 3x3 tile. No image is fetched or generated here, and
// no new image library is involved — the URLs are the ones the library
// already exposes.

// Covers per tile: a 2x2 grid up to four, a 3x3 grid beyond that.
export const MAX_MOSAIC = 9

/**
 * The grid shape for `count` covers, capped at 3x3. `{ columns, rows }`
 * so the caller can pick the matching layout classes.
 */
export function mosaicGrid(count) {
  const total = Math.max(0, Number(count) || 0)
  if (total <= 1) return { columns: 1, rows: 1 }
  if (total === 2) return { columns: 2, rows: 1 }
  if (total <= 4) return { columns: 2, rows: 2 }
  return { columns: 3, rows: 3 }
}

/**
 * A playlist's display cover: its own artwork when it has one, else the
 * first of its track covers — the same pair CoverArt shows for a single
 * playlist. Empty when it has neither.
 */
function playlistCover(playlist) {
  if (!playlist) return ''
  return (
    String(playlist.cover || '') ||
    String((playlist.covers || []).find(Boolean) || '')
  )
}

/**
 * Up to nine cover URLs for a collection, one per member playlist (in
 * the order the collection lists them), skipping members the library
 * doesn't know and duplicates. Empty when there is nothing to show, so
 * the caller falls back to the default cover.
 */
export function collectionCovers(names, playlists, limit = MAX_MOSAIC) {
  const byName = new Map()
  for (const playlist of playlists || []) {
    const key = String(playlist?.name || '')
    if (key) byName.set(key, playlist)
  }
  const covers = []
  const seen = new Set()
  for (const name of names || []) {
    const url = playlistCover(byName.get(String(name)))
    if (!url || seen.has(url)) continue
    seen.add(url)
    covers.push(url)
    if (covers.length >= limit) break
  }
  return covers
}
