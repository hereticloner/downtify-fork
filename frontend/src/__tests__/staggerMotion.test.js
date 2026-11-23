// Staggered entry guard: one capped entry mechanism, no easing drift, and a
// static reduced-motion end state. Mirrors expandedMotion.test.js style.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const indexCss = readFileSync(join(root, 'index.css'), 'utf8')
const tokensCss = readFileSync(join(root, 'styles/tokens.css'), 'utf8')

describe('staggered entry motion', () => {
  it('defines one capped 4px entry keyframe', () => {
    expect(tokensCss).toMatch(
      /@keyframes stagger-in[\s\S]*?transform: translateY\(4px\)/
    )
    expect(tokensCss).toMatch(/@keyframes stagger-in[\s\S]*?transform: none/)
  })

  it('attaches the entry animation with linear 140ms and no forward fill', () => {
    expect(tokensCss).toMatch(
      /\.stagger > \*,\s*\.stagger-fade > \* \{\s*animation: stagger-in 140ms linear backwards;/
    )
    expect(tokensCss).toMatch(/\.stagger-fade > \* \{\s*animation-name: rise;/)
  })

  it('caps stagger delays so the last child settles by 240ms', () => {
    const delays = [...tokensCss.matchAll(/animation-delay: (\d+)ms/g)].map((m) =>
      Number(m[1])
    )
    expect(delays.length).toBeGreaterThanOrEqual(6)
    expect(delays).toContain(0)
    const max = Math.max(...delays)
    expect(max).toBeLessThanOrEqual(100)
    expect(140 + max).toBeLessThanOrEqual(240)
  })

  it('keeps reduced motion at a static final state', () => {
    const reduced = indexCss.match(
      /@media \(prefers-reduced-motion: reduce\)[\s\S]*$/
    )
    expect(reduced).not.toBeNull()
    expect(reduced[0]).toMatch(
      /\.stagger > \*,\s*\.stagger-fade > \* \{\s*animation: none;\s*opacity: 1;\s*transform: none;/
    )
    expect(reduced[0]).toMatch(/\.animate-rise[\s\S]*?animation: none/)
  })

  it('keeps the button press fade unlayered without killing colour transitions', () => {
    const afterComponents = tokensCss.slice(tokensCss.indexOf('@layer components'))
    const block = afterComponents.match(
      /button:not\(:disabled\) \{\s*transition:[\s\S]*?\}/
    )
    expect(block).not.toBeNull()
    expect(block[0]).toMatch(/opacity 80ms linear/)
    expect(block[0]).toMatch(/color 100ms linear/)
    expect(tokensCss).toMatch(
      /button:not\(:disabled\):active \{\s*opacity: 0\.6;/
    )
  })
})
