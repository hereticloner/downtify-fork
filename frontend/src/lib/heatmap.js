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

/** How many days the 30-day trend line spans. */
export const TREND_DAYS = 30

/**
 * The newest `days` cells, oldest first - the window the trend line
 * draws. A shorter window than asked for is all there is.
 */
export function heatmapTrend(cells, days = TREND_DAYS) {
  const span = Math.max(0, Number(days) || 0)
  const rows = Array.isArray(cells) ? cells : []
  return rows.slice(Math.max(0, rows.length - span))
}

/**
 * The numbers the trend panel reads out: how much was played, over how
 * many days, and the best day of the window. `average` is per day
 * played, not per day in the window - a day nobody listened is a zero
 * that says something.
 */
export function heatmapTotals(cells) {
  const rows = Array.isArray(cells) ? cells : []
  const plays = rows.reduce((sum, cell) => sum + (Number(cell?.count) || 0), 0)
  const active = rows.filter((cell) => (Number(cell?.count) || 0) > 0).length
  const best = rows.reduce(
    (peak, cell) =>
      (Number(cell?.count) || 0) > (Number(peak?.count) || 0) ? cell : peak,
    null
  )
  return {
    plays,
    activeDays: active,
    days: rows.length,
    average: active > 0 ? Math.round((plays / active) * 10) / 10 : 0,
    best: best
      ? { date: String(best.date || ''), count: Number(best.count) }
      : null,
  }
}

/**
 * The trend line as an SVG polyline `points` string, oldest day on the
 * left. Scaled to the busiest day in the window rather than to a fixed
 * number, like the grid's shades. `height` is flipped, because SVG y
 * grows downwards.
 */
export function trendPoints(cells, width = 100, height = 28) {
  const rows = Array.isArray(cells) ? cells : []
  if (rows.length < 2) return ''
  const counts = rows.map((cell) => Number(cell?.count) || 0)
  const peak = Math.max(1, ...counts)
  const step = width / (rows.length - 1)
  return counts
    .map(
      (count, i) =>
        `${(i * step).toFixed(2)},${(height - (count / peak) * height).toFixed(2)}`
    )
    .join(' ')
}
