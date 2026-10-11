// Playlist downloads that are still missing tracks (see
// `GET /api/playlists/incomplete`). Used by the Queue page's panel.
import API from '/src/model/api'

/** The API's incomplete-playlist reports. */
export async function loadIncompletePlaylists() {
  const res = await API.getIncompletePlaylists()
  return res.data?.playlists || []
}

/** Queue only the tracks a tracked playlist is still missing. */
export async function downloadMissingPlaylistTracks(playlist) {
  const res = await API.downloadMissingPlaylistTracks({
    spotify_playlist_id: playlist.spotify_playlist_id,
    playlist_url: playlist.playlist_url,
  })
  return res.data
}
