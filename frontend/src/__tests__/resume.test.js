import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({
  api: { getResume: vi.fn() },
}))

vi.mock('/src/model/api', () => ({ default: fixture.api }))

let resume

beforeEach(async () => {
  vi.resetModules()
  vi.clearAllMocks()
  resume = (await import('../model/resume')).useResume()
})

describe('cross-device resume', () => {
  it('stays empty when the server has no position', async () => {
    fixture.api.getResume.mockResolvedValue({ data: { track: null } })

    await resume.load()

    expect(resume.item.value).toBeNull()
    expect(resume.loading.value).toBe(false)
    expect(resume.error.value).toBe(false)
  })

  it('keeps the track, position and device', async () => {
    fixture.api.getResume.mockResolvedValue({
      data: {
        track: { file: 'A - One.mp3', title: 'One', artist: 'A' },
        position: 42,
        duration: 100,
        device_id: 'phone',
      },
    })

    await resume.load()

    expect(resume.item.value).toMatchObject({
      track: { file: 'A - One.mp3' },
      position: 42,
      device_id: 'phone',
    })
  })

  it('dismisses only this visit', async () => {
    fixture.api.getResume.mockResolvedValue({
      data: { track: { file: 'A - One.mp3' }, position: 12 },
    })
    await resume.load()

    resume.dismiss()

    expect(resume.item.value).toBeNull()
  })

  it('does not break Home when the request fails', async () => {
    fixture.api.getResume.mockRejectedValue(new Error('offline'))

    await expect(resume.load()).resolves.toBeUndefined()

    expect(resume.error.value).toBe(true)
    expect(resume.item.value).toBeNull()
  })
})
