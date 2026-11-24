export function artistWatchUrl(spotifyId) {
  const id = String(spotifyId || '').trim()
  return id ? `https://open.spotify.com/artist/${id}` : ''
}

export function isArtistWatched(items, spotifyId) {
  const id = String(spotifyId || '').trim()
  if (!id) return false
  return (items || []).some((item) => {
    if (item?.kind !== 'artist') return false
    try {
      return new URL(item.url).pathname.includes(`/artist/${id}`)
    } catch {
      return false
    }
  })
}
