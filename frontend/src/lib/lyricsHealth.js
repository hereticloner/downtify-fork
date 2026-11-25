export const LYRICS_STATUSES = ['synced', 'plain_only', 'missing']

export function lyricsStatusCounts(report) {
  const counts = Object.fromEntries(LYRICS_STATUSES.map((key) => [key, 0]))
  for (const finding of report?.findings || []) {
    if (finding.status in counts) counts[finding.status] += 1
  }
  return counts
}

export function eligibleLyricsFiles(report, syncedOnly = false) {
  return (report?.findings || [])
    .filter(
      (finding) =>
        finding.status === 'missing' ||
        (syncedOnly && finding.status === 'plain_only')
    )
    .map((finding) => finding.file)
    .filter(Boolean)
}

export function chunkFiles(files = [], size = 100) {
  const chunks = []
  for (let index = 0; index < files.length; index += size) {
    chunks.push(files.slice(index, index + size))
  }
  return chunks
}

export function clampLyricsOffset(value) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return 0
  const rounded = Math.round(Math.min(0.5, Math.max(-0.5, parsed)) * 10) / 10
  return rounded === 0 ? 0 : rounded
}

export function formatLyricsOffset(value) {
  const offset = clampLyricsOffset(value)
  if (offset === 0) return '0.0 s'
  return `${offset > 0 ? '+' : '−'}${Math.abs(offset).toFixed(1)} s`
}

export function lyricsHighlightTime(audioTime, offset) {
  return Number(audioTime || 0) + 0.25 + clampLyricsOffset(offset)
}

export function lyricsSeekTime(lineTime, offset) {
  return Number(lineTime || 0) - clampLyricsOffset(offset)
}

export function lyricsOffsetForDevice(prefs, deviceId) {
  return clampLyricsOffset(prefs?.lyrics_offsets?.[deviceId])
}

export function withLyricsOffset(prefs, deviceId, offset) {
  return {
    ...(prefs || {}),
    lyrics_offsets: {
      ...(prefs?.lyrics_offsets || {}),
      [deviceId]: clampLyricsOffset(offset),
    },
  }
}
