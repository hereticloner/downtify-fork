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
