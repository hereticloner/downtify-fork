// The Stats tab's listening heatmap: how the backend's per-day play
// counts become a GitHub-style grid. Pure, so it's unit-testable
// without mounting anything.

/** Weeks the grid spans - a year, the activity log's retention. */
export const HEATMAP_WEEKS = 52

/** Days in a week column: one cell per weekday. */
export const HEATMAP_DAYS = 7

/** Density levels a cell can be at: nothing, then four shades. */
export const HEATMAP_LEVELS = 4

/**
 * `0` for Sunday, `6` for Saturday - where a day's cell sits in its
 * column. The date arrives as a plain `YYYY-MM-DD`, parsed as UTC so
 * the reader's timezone can't shift a day into the wrong row.
 */
export function weekdayIndex(date) {
  const parsed = Date.parse(`${String(date || '')}T00:00:00Z`)
  if (Number.isNaN(parsed)) return 0
  return new Date(parsed).getUTCDay()
}

/**
 * How dense a cell is, 0 (no plays) to `HEATMAP_LEVELS` (the busiest
 * day shown). Scaled to the busiest day rather than to a fixed number,
 * so a quiet fortnight still reads as a shape.
 */
export function heatmapLevel(count, max) {
  const plays = Number(count) || 0
  const busiest = Number(max) || 0
  if (plays <= 0 || busiest <= 0) return 0
  return Math.min(
    HEATMAP_LEVELS,
    Math.max(1, Math.ceil((plays / busiest) * HEATMAP_LEVELS))
  )
}

/** `[{date, count, level}, ...]` for at most `weeks * 7` days. */
export function heatmapCells(days, weeks = HEATMAP_WEEKS) {
  const span = Math.max(0, Number(weeks) || 0) * HEATMAP_DAYS
  const rows = (Array.isArray(days) ? days : []).slice(-span)
  const max = rows.reduce(
    (peak, day) => Math.max(peak, Number(day?.count) || 0),
    0
  )
  return rows.map((day) => ({
    date: String(day?.date || ''),
    count: Number(day?.count) || 0,
    level: heatmapLevel(day?.count, max),
  }))
}

/** The grid split into week columns, oldest week first. */
export function heatmapColumns(cells) {
  const columns = []
  const rows = Array.isArray(cells) ? cells : []
  for (let i = 0; i < rows.length; i += HEATMAP_DAYS) {
    columns.push(rows.slice(i, i + HEATMAP_DAYS))
  }
  return columns
}

/**
 * Empty cells the first column needs above its first day so the columns
 * line up with weekdays (a year of days rarely starts on a Sunday).
 * Read off the same trimmed window the grid draws.
 */
export function heatmapLead(cells) {
  return weekdayIndex(Array.isArray(cells) ? cells[0]?.date : '')
}
