import { describe, expect, it } from 'vitest'

import {
  clampLyricsOffset,
  formatLyricsOffset,
  lyricsHighlightTime,
  lyricsOffsetForDevice,
  lyricsSeekTime,
  withLyricsOffset,
} from '../lib/lyricsHealth'

describe('lyrics offset timing', () => {
  it('clamps to ±0.5 seconds in 0.1-second steps', () => {
    expect(clampLyricsOffset(undefined)).toBe(0)
    expect(clampLyricsOffset(Number.NaN)).toBe(0)
    expect(clampLyricsOffset(0.26)).toBe(0.3)
    expect(clampLyricsOffset(9)).toBe(0.5)
    expect(clampLyricsOffset(-9)).toBe(-0.5)
  })

  it('formats a signed seconds value', () => {
    expect(formatLyricsOffset(0)).toBe('0.0 s')
    expect(formatLyricsOffset(0.3)).toBe('+0.3 s')
    expect(formatLyricsOffset(-0.3)).toBe('−0.3 s')
  })

  it('shifts highlight and seek in opposite directions', () => {
    expect(lyricsHighlightTime(10, 0.3)).toBe(10.55)
    expect(lyricsSeekTime(10, 0.3)).toBe(9.7)
  })

  it('keeps offsets per device and preserves other devices', () => {
    const prefs = { lyrics_offsets: { phone: -0.2, tablet: 0.4 } }
    expect(lyricsOffsetForDevice(prefs, 'phone')).toBe(-0.2)
    expect(lyricsOffsetForDevice(prefs, 'unknown')).toBe(0)
    expect(withLyricsOffset(prefs, 'phone', 9)).toEqual({
      lyrics_offsets: { phone: 0.5, tablet: 0.4 },
    })
  })
})
