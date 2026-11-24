import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({
  api: { getStats: vi.fn() },
}))

vi.mock('/src/model/api', () => ({ default: fixture.api }))

import { formatDuration, formatPercent } from '../lib/format'

let stats

beforeEach(async () => {
  vi.resetModules()
  vi.clearAllMocks()
  fixture.api.getStats.mockResolvedValue({ data: { playback: {} } })
  stats = (await import('../model/stats')).useStats()
})

describe('Stats period', () => {
  it('starts at 30 days and sends the selected period', async () => {
    expect(stats.days.value).toBe(30)

    await stats.load()
    expect(fixture.api.getStats).toHaveBeenLastCalledWith({
      days: 30,
      scope: 'user',
    })

    stats.days.value = 7
    await stats.load()
    expect(fixture.api.getStats).toHaveBeenLastCalledWith({
      days: 7,
      scope: 'user',
    })

    stats.days.value = 90
    await stats.load()
    expect(fixture.api.getStats).toHaveBeenLastCalledWith({
      days: 90,
      scope: 'user',
    })
  })
})

describe('listening metric formatting', () => {
  it('formats hours of listening', () => {
    expect(formatDuration(3661)).toBe('1:01:01')
  })

  it('formats completion and skip rates', () => {
    expect(formatPercent(0.875)).toBe('88%')
    expect(formatPercent(0)).toBe('0%')
    expect(formatPercent(1)).toBe('100%')
  })
})
