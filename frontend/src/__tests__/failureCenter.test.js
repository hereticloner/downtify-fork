import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({
  api: {
    getDownloadFailures: vi.fn(),
    retryDownloadFailure: vi.fn(),
    clearDownloadFailures: vi.fn(),
  },
}))

vi.mock('/src/model/api', () => ({ default: fixture.api }))

let failures

beforeEach(async () => {
  vi.resetModules()
  vi.clearAllMocks()
  failures = (await import('../model/downloadFailures')).useDownloadFailures()
})

describe('persistent download failures', () => {
  it('starts empty and keeps server rows', async () => {
    fixture.api.getDownloadFailures.mockResolvedValue({
      data: {
        items: [
          {
            song_id: 'track-1',
            song: { name: 'One' },
            message: 'No audio match',
            attempts: 2,
          },
        ],
        count: 1,
      },
    })

    await failures.load()

    expect(failures.items.value).toHaveLength(1)
    expect(failures.items.value[0]).toMatchObject({
      song_id: 'track-1',
      attempts: 2,
    })
  })

  it('retries and clears through the API', async () => {
    fixture.api.retryDownloadFailure.mockResolvedValue({
      data: { queued: true, song_id: 'track-1' },
    })
    fixture.api.clearDownloadFailures.mockResolvedValue({
      data: { cleared: 1 },
    })
    fixture.api.getDownloadFailures.mockResolvedValue({
      data: { items: [{ song_id: 'open', message: 'failed' }], count: 1 },
    })

    await failures.retry('track-1')
    await failures.clear()

    expect(fixture.api.retryDownloadFailure).toHaveBeenCalledWith('track-1')
    expect(fixture.api.clearDownloadFailures).toHaveBeenCalledOnce()
    expect(fixture.api.getDownloadFailures).toHaveBeenCalledTimes(2)
    expect(failures.items.value.map((row) => row.song_id)).toEqual(['open'])
  })

  it('does not break Queue when loading fails', async () => {
    fixture.api.getDownloadFailures.mockRejectedValue(new Error('offline'))

    await expect(failures.load()).resolves.toBeUndefined()

    expect(failures.error.value).toBe(true)
    expect(failures.items.value).toEqual([])
  })
})
