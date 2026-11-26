const KINDS = new Set(['playlist', 'artist', 'album'])

function validId(value) {
  const id = String(value || '').trim()
  return id && !id.includes('/') && !id.includes(':') ? id : ''
}

function normalizeSpotifyContext(value) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  if (raw.startsWith('spotify:')) {
    const parts = raw.split(':')
    if (parts[1] === 'user' && parts[2] && KINDS.has(parts[3])) {
      const id = validId(parts[4])
      return id ? `spotify:${parts[3]}:${id}` : ''
    }
    if (KINDS.has(parts[1])) {
      const id = validId(parts.slice(2).join(':'))
      return id ? `spotify:${parts[1]}:${id}` : ''
    }
    return ''
  }
  try {
    const url = new URL(raw)
    let parts = url.pathname.split('/').filter(Boolean)
    if (url.hostname === 'api.spotify.com') {
      const kind = parts[1]?.replace(/s$/, '')
      if (parts[0] !== 'v1' || !KINDS.has(kind)) return ''
      const id = validId(parts[2])
      return id ? `spotify:${kind}:${id}` : ''
    }
    if (url.hostname !== 'open.spotify.com') return ''
    if (parts[0]?.startsWith('intl-')) parts = parts.slice(1)
    if (!KINDS.has(parts[0])) return ''
    const id = validId(parts[1])
    return id ? `spotify:${parts[0]}:${id}` : ''
  } catch {
    return ''
  }
}

export function spotifyContextKind(value) {
  const key = normalizeSpotifyContext(value)
  return key ? key.split(':')[1] : ''
}

export function contextLabel(value, labels = {}, t) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  const key = normalizeSpotifyContext(raw)
  const resolved = labels?.[key] || labels?.[raw]
  if (resolved) return String(resolved)
  const kind = spotifyContextKind(raw)
  if (!kind) return raw
  const suffix = kind[0].toUpperCase() + kind.slice(1)
  return t(`stats.contextSpotify${suffix}`)
}
