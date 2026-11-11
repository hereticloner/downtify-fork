import { describe, expect, it } from 'vitest'
import { heroTintColor } from '../lib/heroTint.js'

describe('heroTintColor', () => {
  it('returns null without a palette', () => {
    expect(heroTintColor(null)).toBeNull()
    expect(heroTintColor(undefined)).toBeNull()
    expect(heroTintColor({})).toBeNull()
    expect(heroTintColor({ secondary: '#123456' })).toBeNull()
  })

  it('washes from the palette primary', () => {
    expect(heroTintColor({ primary: '#1a8033' })).toBe(
      'color-mix(in srgb, #1a8033 55%, transparent)'
    )
  })

  it('leaves the legacy hue fallback to the caller', () => {
    expect(heroTintColor({ primary: '#1a8033' })).not.toContain('oklch')
  })
})
