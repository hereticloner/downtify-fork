// Staggered entry guard: one capped springy mechanism, and a static
// reduced-motion end state. Mirrors the rewritten motion guards.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const indexCss = readFileSync(join(root, 'index.css'), 'utf8')
const tokensCss = readFileSync(join(root, 'styles/tokens.css'), 'utf8')

describe('staggered entry motion', () => {
  it('defines one springy 10px entry keyframe', () => {
    expect(tokensCss).toMatch(
      /@keyframes stagger-in[\s\S]*?transform: translateY\(10px\) scale\(0\.97\)/
    )
    expect(tokensCss).toMatch(/@keyframes stagger-in[\s\S]*?transform: translateY\(0\) scale\(1\)/)
  })

  it('attaches the entry animation with springy 300ms and no forward fill', () => {
    expect(tokensCss).toMatch(
      /\.stagger > \*,\s*\.stagger-fade > \* \{\s*animation: stagger-in 300ms cubic-bezier\(0\.34, 1\.4, 0\.64, 1\) backwards;/
    )
    expect(tokensCss).toMatch(/\.stagger-fade > \* \{\s*animation-name: rise;/)
  })

  it('caps stagger delays so the last child settles inside 500ms', () => {
    const delays = [...tokensCss.matchAll(/animation-delay: (\d+)ms/g)].map((m) =>
      Number(m[1])
    )
    expect(delays.length).toBeGreaterThanOrEqual(6)
    expect(delays).toContain(0)
    const max = Math.max(...delays)
    expect(max).toBeLessThanOrEqual(125)
    expect(300 + max).toBeLessThanOrEqual(500)
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

  it('keeps the button feedback unlayered without killing colour transitions', () => {
    const afterComponents = tokensCss.slice(tokensCss.indexOf('@layer components'))
    const block = afterComponents.match(
      /button:not\(:disabled\) \{\s*transition:[\s\S]*?\}/
    )
    expect(block).not.toBeNull()
    expect(block[0]).toMatch(/opacity 160ms cubic-bezier/)
    expect(block[0]).toMatch(/color 200ms ease/)
    expect(afterComponents).toMatch(
      /button:not\(:disabled\):hover \{\s*transform: scale\(1\.02\);/
    )
    expect(afterComponents).toMatch(
      /button:not\(:disabled\):active \{[\s\S]*?transform: scale\(1\.04\);/
    )
  })
})
