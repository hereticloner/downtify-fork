import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const featureIndex = readFileSync(
  new URL('../../features/index.md', import.meta.url),
  'utf8'
)
const apiReference = readFileSync(
  new URL('../../api-reference.md', import.meta.url),
  'utf8'
)

describe('Stats documentation contract', () => {
  it('advertises the listening profile instead of removed dashboard panels', () => {
    const row = featureIndex
      .split('\n')
      .find((line) => line.startsWith('| [Stats](stats.md)'))

    expect(row).toContain('listening profile')
    expect(row).toContain('four-week report')
    expect(row).not.toMatch(/downloads-per-day|heatmap|playlists you played from/)
  })

  it('documents playback context as retained API data, not a rendered panel', () => {
    const start = apiReference.indexOf('### `POST /api/activity/playback`')
    const end = apiReference.indexOf('\n---', start)
    const section = apiReference.slice(start, end)

    expect(section).toContain('stores them with the canonical play')
    expect(section).toContain('and returns them through the [Stats API](#stats)')
    expect(section).not.toContain('page shows as "played from"')
  })
})
