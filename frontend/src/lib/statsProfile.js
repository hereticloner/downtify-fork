function text(value) {
  return String(value || '').trim()
}

export function trackParts(row) {
  const artist = text(row?.artist)
  const title = text(row?.title)
  const album = text(row?.album)
  if (artist || title) return { artist, title, album }

  const summary = text(row?.summary)
  const separator = summary.indexOf(' - ')
  if (separator > 0) {
    return {
      artist: summary.slice(0, separator),
      title: summary.slice(separator + 3),
      album,
    }
  }
  return { artist, title: summary, album }
}

export function weekLabel(start, end, locale = 'en') {
  const from = Date.parse(`${text(start)}T00:00:00Z`)
  const to = Date.parse(`${text(end)}T00:00:00Z`)
  if (!Number.isFinite(from) || !Number.isFinite(to)) return ''
  const format = new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
  return `${format.format(from)} – ${format.format(to)}`
}
