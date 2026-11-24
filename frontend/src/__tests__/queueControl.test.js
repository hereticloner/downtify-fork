import { describe, expect, it } from 'vitest'

import {
  blankQueueControl,
  mergeQueueControl,
  queueBulkRequest,
  queuePriorityRequest,
  selectableQueueIds,
  sortQueueItems,
} from '../lib/queueControl'

const queued = (id, priority = 'normal') => ({
  key: id,
  state: 'queued',
  priority,
})

describe('queue control settings', () => {
  it('merges missing quiet-hour fields over safe defaults', () => {
    expect(blankQueueControl()).toEqual({
      quiet_hours: {
        enabled: false,
        start: '22:00',
        end: '08:00',
        timezone: 'Europe/Istanbul',
      },
    })
    expect(
      mergeQueueControl({ quiet_hours: { enabled: true, start: '23:00' } })
    ).toEqual({
      quiet_hours: {
        enabled: true,
        start: '23:00',
        end: '08:00',
        timezone: 'Europe/Istanbul',
      },
    })
  })
})

describe('queue selection and ordering', () => {
  it('sorts high priority first and keeps FIFO within a priority', () => {
    const rows = [
      queued('normal-1'),
      queued('high-1', 'high'),
      queued('normal-2'),
      queued('high-2', 'high'),
    ]

    expect(sortQueueItems(rows).map((row) => row.key)).toEqual([
      'high-1',
      'high-2',
      'normal-1',
      'normal-2',
    ])
    expect(rows.map((row) => row.key)).toEqual([
      'normal-1',
      'high-1',
      'normal-2',
      'high-2',
    ])
  })

  it('selects only waiting jobs and removes duplicate ids', () => {
    const rows = [
      queued('a'),
      { key: 'active', state: 'active' },
      queued('b'),
      queued('a'),
      { key: 'done', state: 'done' },
    ]

    expect(selectableQueueIds(rows)).toEqual(['a', 'b'])
  })

  it('builds deduplicated API requests', () => {
    expect(queuePriorityRequest(['a', 'a', 'b'], 'high')).toEqual({
      song_ids: ['a', 'b'],
      priority: 'high',
    })
    expect(queueBulkRequest('pause', ['b', 'b', 'a'])).toEqual({
      action: 'pause',
      song_ids: ['b', 'a'],
    })
    expect(() => queuePriorityRequest(['a'], 'urgent')).toThrow()
    expect(() => queueBulkRequest('delete', ['a'])).toThrow()
  })
})
