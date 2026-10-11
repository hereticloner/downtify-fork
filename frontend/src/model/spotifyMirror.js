// Spotify Mirror test actions (see downtify/spotify_mirror.py).
import API from '/src/model/api'

/**
 * Mirror one track's play to the connected Spotify device now, skipping
 * the mirror's own dedupe - it is an admin's manual test. `track` is a
 * library track row (`{ file, title, artist, ... }`).
 */
export async function mirrorNow(track) {
  const res = await API.spotifyMirrorNow(track)
  return res.data
}
