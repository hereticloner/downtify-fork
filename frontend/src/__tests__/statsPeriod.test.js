import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({
  api: { getStats: vi.fn() },
}))

vi.mock('/src/model/api', () => ({ default: fixture.api }))

import { formatDuration, formatPercent } from '../lib/format'
import { playsForDay } from '../model/stats'

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

  it('loads an exact day in the background without blanking the page', async () => {
    fixture.api.getStats.mockResolvedValue({
      data: { playback: { day: { date: '2026-11-20', total: 1, plays: [] } } },
    })

    await stats.load('2026-11-20', { background: true })

    expect(fixture.api.getStats).toHaveBeenCalledWith({
      days: 30,
      scope: 'user',
      date: '2026-11-20',
    })
    expect(stats.loading.value).toBe(false)
    expect(stats.dayLoading.value).toBe(false)
    expect(stats.dayError.value).toBe(false)
  })

  it('ignores a stale response after a newer day request', async () => {
    let resolveFirst
    let resolveSecond
    fixture.api.getStats
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve
          })
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve
          })
      )

    const first = stats.load('2026-11-20', { background: true })
    const second = stats.load('2026-11-21', { background: true })
    resolveSecond({ data: { playback: { day: { date: '2026-11-21' } } } })
    await second
    resolveFirst({ data: { playback: { day: { date: '2026-11-20' } } } })
    await first

    expect(stats.stats.value.playback.day.date).toBe('2026-11-21')
  })

  it('keeps day errors separate from whole-page errors', async () => {
    fixture.api.getStats.mockRejectedValue(new Error('offline'))

    await stats.load('2026-11-20', { background: true })

    expect(stats.error.value).toBe(false)
    expect(stats.dayError.value).toBe(true)
    expect(stats.loading.value).toBe(false)
  })
})

describe('playsForDay', () => {
  it('uses recent plays when no day is selected', () => {
    expect(
      playsForDay({ playback: { recent: [{ summary: 'Recent' }] } }, '')
    ).toEqual([{ summary: 'Recent' }])
  })

  it('uses the exact server day page when a day is selected', () => {
    expect(
      playsForDay(
        {
          playback: {
            recent: [{ summary: 'Recent' }],
            day: {
              date: '2026-11-20',
              plays: [{ summary: 'Older exact day' }],
            },
          },
        },
        '2026-11-20'
      )
    ).toEqual([{ summary: 'Older exact day' }])
  })

  it('returns an empty list for a selected day with no response yet', () => {
    expect(
      playsForDay(
        { playback: { recent: [{ summary: 'Recent' }] } },
        '2026-11-20'
      )
    ).toEqual([])
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
