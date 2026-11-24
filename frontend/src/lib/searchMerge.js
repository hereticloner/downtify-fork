import { songKey } from './library'

export function mergeSearchResults(localTracks = [], remoteTracks = []) {
  const localKeys = []
  for (const track of localTracks || []) {
    const key = songKey(track.artist, track.title)
    if (key && !localKeys.includes(key)) localKeys.push(key)
  }
  const known = new Set(localKeys)
  const tracks = (remoteTracks || []).map((track) => {
    const artist = track.artist || (track.artists || []).join(', ')
    const key = songKey(artist, track.title || track.name)
    return { ...track, inLibrary: known.has(key) }
  })
  return { tracks, localKeys }
}
