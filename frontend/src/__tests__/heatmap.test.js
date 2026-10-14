import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

import ActivityHeatmap from '/src/components/library/ActivityHeatmap.vue'
import {
  HEATMAP_DAYS,
  HEATMAP_LEVELS,
  HEATMAP_WEEKS,
  heatmapCells,
  heatmapColumns,
  heatmapLead,
  heatmapLevel,
  weekdayIndex,
} from '/src/lib/heatmap'

/**
 * A dense window of days ending today, the way `build_stats` sends it:
 * one `{date, count}` per day, oldest first, empty days included.
 */
function year(counts = {}) {
  const today = new Date()
  const days = []
  for (let i = HEATMAP_WEEKS * HEATMAP_DAYS - 1; i >= 0; i -= 1) {
    const day = new Date(
      Date.UTC(
        today.getUTCFullYear(),
        today.getUTCMonth(),
        today.getUTCDate() - i
      )
    )
    const date = day.toISOString().slice(0, 10)
    days.push({ date, count: counts[date] ?? 0 })
  }
  return days
}

const cellsIn = (html) => html.match(/data-date="/g) || []

describe('weekdayIndex', () => {
  it('puts a day in its own row, parsed as UTC', () => {
    expect(weekdayIndex('2026-10-11')).toBe(0) // Sunday
    expect(weekdayIndex('2026-10-12')).toBe(1) // Monday
    expect(weekdayIndex('2026-10-17')).toBe(6) // Saturday
  })

  it('falls back to the first row for an unusable date', () => {
    expect(weekdayIndex('')).toBe(0)
    expect(weekdayIndex('nonsense')).toBe(0)
    expect(weekdayIndex(undefined)).toBe(0)
  })
})

describe('heatmapLevel', () => {
  it('is empty without plays', () => {
    expect(heatmapLevel(0, 20)).toBe(0)
    expect(heatmapLevel(5, 0)).toBe(0)
  })

  it('steps up with the count, capped at the busiest day', () => {
    expect(heatmapLevel(1, 4)).toBe(1)
    expect(heatmapLevel(2, 4)).toBe(2)
    expect(heatmapLevel(3, 4)).toBe(3)
    expect(heatmapLevel(4, 4)).toBe(HEATMAP_LEVELS)
    // Never past the top shade, however far over it a day goes.
    expect(heatmapLevel(400, 4)).toBe(HEATMAP_LEVELS)
  })

  it('scales to the window, so a quiet week still reads', () => {
    expect(heatmapLevel(1, 1)).toBe(HEATMAP_LEVELS)
  })
})

describe('heatmapCells', () => {
  it('carries one cell per day of the window, at its own level', () => {
    const days = year({ '2026-01-01': 0 })
    days[0].count = 4
    const cells = heatmapCells(days)
    expect(cells).toHaveLength(HEATMAP_WEEKS * HEATMAP_DAYS)
    expect(cells[0].level).toBe(HEATMAP_LEVELS)
    expect(cells.at(-1).date).toBe(days.at(-1).date)
    expect(cells.every((cell) => cell.count === 0 || cell.level > 0)).toBe(true)
  })

  it('takes the last `weeks` when given more than asked for', () => {
    const cells = heatmapCells(year(), 2)
    expect(cells).toHaveLength(2 * HEATMAP_DAYS)
    expect(cells[0].date).toBe(year().at(-14).date)
  })

  it('copes with a panel the server never filled', () => {
    expect(heatmapCells(undefined)).toEqual([])
    expect(heatmapCells(null, 0)).toEqual([])
    expect(heatmapCells([{ date: '', count: 'x' }], 1)[0].level).toBe(0)
  })
})

describe('heatmapColumns', () => {
  it('splits the days into week columns of seven', () => {
    const columns = heatmapColumns(heatmapCells(year(), 4))
    expect(columns).toHaveLength(4)
    expect(columns.every((week) => week.length === HEATMAP_DAYS)).toBe(true)
  })

  it('leads the first column by its weekday, so rows line up', () => {
    // 2026-01-04 is a Sunday, 2026-01-05 a Monday.
    expect(
      heatmapLead(heatmapCells([{ date: '2026-01-05', count: 1 }], 1))
    ).toBe(1)
    expect(
      heatmapLead(heatmapCells([{ date: '2026-01-04', count: 1 }], 1))
    ).toBe(0)
    expect(heatmapLead([])).toBe(0)
  })
})

describe('ActivityHeatmap', () => {
  it('renders a cell for every day of the window', async () => {
    const html = await render(ActivityHeatmap, { days: year() })
    expect(cellsIn(html)).toHaveLength(HEATMAP_WEEKS * HEATMAP_DAYS)
  })

  it('colours a cell by how much was played', async () => {
    const days = year()
    days.at(-1).count = 9
    days.at(-2).count = 0
    const html = await render(ActivityHeatmap, { days })
    const rendered = html
      .split('<span')
      .filter((tag) => tag.includes('data-date'))
    const today = rendered.at(-1)
    const yesterday = rendered.at(-2)
    expect(today).toContain('bg-accent ')
    expect(today).toContain('data-date=')
    expect(yesterday).toContain('bg-line-2')
    expect(html).toContain(`${days.at(-1).date}: 9`)
  })

  it('honours a narrower window', async () => {
    const html = await render(ActivityHeatmap, { days: year(), weeks: 4 })
    expect(cellsIn(html)).toHaveLength(4 * HEATMAP_DAYS)
  })

  it('renders an empty grid rather than failing on no data', async () => {
    expect(cellsIn(await render(ActivityHeatmap, {}))).toHaveLength(0)
  })
})

/** Server-render a component with props, the way the app mounts it. */
function render(component, props) {
  const app = createSSRApp({ render: () => h(component, props) })
  return renderToString(app)
}
