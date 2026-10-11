// Write an M3U file for a playlist on demand (see
// `POST /api/playlist/m3u`), for playlists whose download is already done.
import API from '/src/model/api'
import { m3uEntries } from '/src/lib/m3u'

/**
 * Ask the server to write the M3U for a playlist URL using the tracks
 * that are already in the library. `playlistUrl` is a Spotify or YouTube
 * Music playlist link.
 */
export async function writePlaylistM3u(playlistUrl, tracks) {
  const res = await API.writePlaylistM3u({
    playlist_url: playlistUrl,
    tracks: m3uEntries(tracks),
  })
  return res.data
}
