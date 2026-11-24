import { beforeEach, describe, expect, it, vi } from 'vitest'

const { jobs, listeners, getQueue } = vi.hoisted(() => {
  const jobs = [
    {
      song: { song_id: 'normal', name: 'Normal' },
      status: 'queued',
      priority: 'normal',
    },
    {
      song: { song_id: 'high', name: 'High' },
      status: 'queued',
      priority: 'high',
    },
    {
      song: { song_id: 'paused', name: 'Paused' },
      status: 'paused',
      priority: 'normal',
    },
  ]
  return {
    jobs,
    listeners: [],
    getQueue: vi.fn(async () => ({ data: jobs })),
  }
})

vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({ data: { signed_in: true, user: { role: 'admin' } } }),
    onMessage(fn) {
      listeners.push(fn)
      return () => {}
    },
    getQueue,
    getSettings: () => Promise.resolve({ data: {} }),
    downloadFileURL: (name) => name,
  },
}))

import { syncQueueFromServer, useProgressTracker } from '../model/download'

describe('queue priority and paused state', () => {
  beforeEach(async () => {
    await syncQueueFromServer()
  })

  it('keeps server priority on each item', () => {
    const { downloadQueue } = useProgressTracker()
    const byId = new Map(downloadQueue.value.map((item) => [item.key, item]))
    expect(byId.get('normal').priority).toBe('normal')
    expect(byId.get('high').priority).toBe('high')
  })

  it('shows an individually paused job as waiting, not active', () => {
    const { downloadQueue } = useProgressTracker()
    const paused = downloadQueue.value.find((item) => item.key === 'paused')
    expect(paused.web_status).toBe('Paused')
    expect(paused.state).toBe('queued')
  })

  it('follows paused and queued WebSocket states', () => {
    const { downloadQueue } = useProgressTracker()
    const paused = downloadQueue.value.find((item) => item.key === 'paused')
    listeners[0]({ song: paused.song, status: 'queued' })
    expect(paused.web_status).toBe('In Queue')
    listeners[0]({ song: paused.song, status: 'paused' })
    expect(paused.web_status).toBe('Paused')
  })
})
