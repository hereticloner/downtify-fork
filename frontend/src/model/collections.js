// Collections: named groups of library playlists (see
// downtify/collections.py). The endpoints are the same the Collections
// page reads; keeping them here instead of a raw fetch makes them
// mockable in tests.
import API from '/src/model/api'

/** The API's collection list: `[{ name, playlists: [...] }]`. */
export async function listCollections() {
  const res = await API.listCollections()
  return res.data || []
}

export async function createCollection(name) {
  const res = await API.createCollection(name)
  return res.data
}

/** Rename one collection; the playlists inside keep their names. */
export async function renameCollection(name, newName) {
  const res = await API.renameCollection(name, newName)
  return res.data
}

export async function editCollectionItems(
  name,
  { add = [], remove = [] } = {}
) {
  const res = await API.editCollectionItems(name, { add, remove })
  return res.data
}

export async function deleteCollection(name) {
  const res = await API.deleteCollection(name)
  return res.data
}

/** One collection with its static members unioned with its rule-derived
 *  ones (the smart-collection view). */
export async function getCollection(name) {
  const res = await API.getCollection(name)
  return res.data
}

/** Replace a collection's rule list; an empty list makes it static again. */
export async function saveCollectionRules(name, rules) {
  const res = await API.saveCollectionRules(name, rules)
  return res.data
}

/**
 * Queue the missing tracks of each member playlist (from
 * `collectionMissingPlaylists`) through the existing per-playlist
 * endpoint. Returns the total number of tracks queued.
 */
export async function downloadCollectionMissing(members) {
  let count = 0
  for (const member of members || []) {
    const res = await API.downloadMissingPlaylistTracks({
      spotify_playlist_id: member.spotify_playlist_id,
      playlist_url: member.playlist_url,
    })
    count += Number(res.data?.missing_count ?? res.data?.count ?? 0)
  }
  return count
}
