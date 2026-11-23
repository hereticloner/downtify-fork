// Expanded motion families guard: bans lifted, so this pins the NEW reality —
// springy 150-500ms families, glow/scale feedback, and static reduced motion.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const indexCss = readFileSync(join(root, 'index.css'), 'utf8')
const tokensCss = readFileSync(join(root, 'styles/tokens.css'), 'utf8')

const maxMs = (block) => {
  const found = [...block.matchAll(/(\d+)ms/g)].map((m) => Number(m[1]))
  return found.length ? Math.max(...found) : Infinity
}

describe('expanded expressive motion families', () => {
  it('uses springy toast transitions in the smooth band', () => {
    const block = tokensCss.match(
      /\.toast-enter-active,[\s\S]*?transition:([\s\S]*?);/
    )
    expect(block).not.toBeNull()
    expect(block[1]).toMatch(/cubic-bezier\(0\.34, 1\.4, 0\.64, 1\)/)
    expect(maxMs(block[1])).toBeLessThanOrEqual(500)
    expect(maxMs(block[1])).toBeGreaterThanOrEqual(150)
  })

  it('uses springy stat reveal', () => {
    expect(tokensCss).toMatch(
      /--animate-stat: stat-reveal 320ms cubic-bezier\(0\.34, 1\.4, 0\.64, 1\) both;/
    )
    const block = tokensCss.match(/\.stat-reveal \{\s*animation: ([^;]+);/)
    expect(block).not.toBeNull()
    expect(block[1]).toMatch(/cubic-bezier\(0\.34, 1\.4, 0\.64, 1\)/)
    expect(maxMs(block[1])).toBeLessThanOrEqual(500)
  })

  it('moves reordered list rows with springy transform', () => {
    expect(indexCss).toMatch(
      /\.list-move[\s\S]*?transform 280ms cubic-bezier\(0\.34, 1\.4, 0\.64, 1\)/
    )
  })

  it('keeps glow and scale inside the structural language', () => {
    expect(tokensCss).toMatch(/box-shadow: 0 0 0 3px color-mix/)
    expect(tokensCss).toMatch(/scale\(1\.05\)/)
    expect(tokensCss).toMatch(/--radius-control: 0px;/)
  })

  it('gives reduced-motion a static end state for new families', () => {
    const reduced = indexCss.match(
      /@media \(prefers-reduced-motion: reduce\)[\s\S]*$/
    )
    expect(reduced).not.toBeNull()
    expect(reduced[0]).toMatch(/\.toast-[a-z-]+/)
    expect(reduced[0]).toMatch(/\.stat-reveal/)
    expect(reduced[0]).toMatch(/\.list-move/)
    expect(reduced[0]).toMatch(/\.play-glow[\s\S]*?box-shadow: none;/)
  })
})
