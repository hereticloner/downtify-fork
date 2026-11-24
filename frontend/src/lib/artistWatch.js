export function artistWatchUrl(spotifyId) {
  const id = String(spotifyId || '').trim()
  return id ? `https://open.spotify.com/artist/${id}` : ''
}

export function isArtistWatched(items, spotifyId) {
  const id = String(spotifyId || '').trim()
  if (!id) return false
  return (items || []).some(
    (item) => item?.kind === 'artist' && String(item.spotify_id || '') === id
  )
}
