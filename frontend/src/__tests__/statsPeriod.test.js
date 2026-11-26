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

  it('merges background day detail without replacing base stats', async () => {
    stats.stats.value = {
      library: { tracks: 7 },
      playback: { recent: [{ summary: 'Recent' }] },
    }
    fixture.api.getStats.mockResolvedValue({
      data: {
        library: { tracks: 999 },
        playback: {
          day: { date: '2026-11-20', total: 1, plays: [] },
          context_labels: { 'spotify:playlist:abc': 'Playlist' },
        },
      },
    })

    await stats.load('2026-11-20', { background: true })

    expect(stats.stats.value.library.tracks).toBe(7)
    expect(stats.stats.value.playback.recent).toEqual([{ summary: 'Recent' }])
    expect(stats.stats.value.playback.day.date).toBe('2026-11-20')
    expect(stats.stats.value.playback.context_labels).toEqual({
      'spotify:playlist:abc': 'Playlist',
    })
  })

  it('loads and selects exact pattern detail in the background', async () => {
    fixture.api.getStats.mockResolvedValue({
      data: {
        playback: {
          pattern_detail: { kind: 'hour', bucket: 14, total: 2 },
          context_labels: { 'spotify:artist:abc': 'Artist' },
        },
      },
    })

    await stats.loadPattern('hour', 14)

    expect(fixture.api.getStats).toHaveBeenCalledWith({
      days: 30,
      scope: 'user',
      pattern: 'hour',
      bucket: 14,
    })
    expect(stats.selectedPattern.value).toEqual({ kind: 'hour', bucket: 14 })
    expect(stats.stats.value.playback.pattern_detail.total).toBe(2)
    expect(stats.patternLoading.value).toBe(false)
    expect(stats.patternError.value).toBe(false)
  })

  it('ignores stale pattern responses', async () => {
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

    const first = stats.loadPattern('hour', 14)
    const second = stats.loadPattern('hour', 15)
    resolveSecond({
      data: { playback: { pattern_detail: { kind: 'hour', bucket: 15 } } },
    })
    await second
    resolveFirst({
      data: { playback: { pattern_detail: { kind: 'hour', bucket: 14 } } },
    })
    await first

    expect(stats.stats.value.playback.pattern_detail.bucket).toBe(15)
    expect(stats.selectedPattern.value.bucket).toBe(15)
  })

  it('keeps pattern errors separate and supports clear', async () => {
    fixture.api.getStats.mockRejectedValue(new Error('offline'))

    await stats.loadPattern('weekday', 1)

    expect(stats.error.value).toBe(false)
    expect(stats.patternError.value).toBe(true)
    stats.clearPattern()
    expect(stats.selectedPattern.value).toBeNull()
    expect(stats.patternError.value).toBe(false)
    expect(stats.stats.value.playback?.pattern_detail?.kind).toBe('')
  })

  it('keeps pattern selection on a foreground period reload', async () => {
    fixture.api.getStats.mockResolvedValue({
      data: { playback: { pattern_detail: { kind: 'hour', bucket: 14 } } },
    })
    await stats.loadPattern('hour', 14)
    stats.days.value = 7
    fixture.api.getStats.mockResolvedValue({
      data: { playback: { pattern_detail: { kind: 'hour', bucket: 14 } } },
    })

    await stats.load()

    expect(fixture.api.getStats).toHaveBeenLastCalledWith({
      days: 7,
      scope: 'user',
      pattern: 'hour',
      bucket: 14,
    })
    expect(stats.selectedPattern.value).toEqual({ kind: 'hour', bucket: 14 })
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
