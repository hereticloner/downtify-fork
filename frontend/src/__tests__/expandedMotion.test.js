// Expanded motion families guard: the added families must stay inside the
// pinned v4 doctrine (stepped, short, opacity/transform only, no glow/spring).
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const indexCss = readFileSync(join(root, 'index.css'), 'utf8')
const tokensCss = readFileSync(join(root, 'styles/tokens.css'), 'utf8')
const css = indexCss + tokensCss

const maxMs = (block) => {
  const found = [...block.matchAll(/(\d+)ms/g)].map((m) => Number(m[1]))
  return found.length ? Math.max(...found) : Infinity
}

describe('expanded diagnostic motion families', () => {
  it('uses short stepped toast transitions', () => {
    const block = tokensCss.match(
      /\.toast-enter-active[\s\S]*?transition:([^;]+);/
    )
    expect(block).not.toBeNull()
    expect(block[1]).toMatch(/steps\(3, end\)/)
    expect(maxMs(block[1])).toBeLessThanOrEqual(200)
  })

  it('uses short stepped stat reveal', () => {
    expect(tokensCss).toMatch(/--animate-stat:[^;]*steps\(4, end\)[^;]*;/)
    const block = tokensCss.match(/\.stat-reveal[\s\S]*?\}/)
    expect(block).not.toBeNull()
    expect(maxMs(block[0])).toBeLessThanOrEqual(240)
  })

  it('moves reordered list rows with transform', () => {
    expect(indexCss).toMatch(/\.list-move[\s\S]*?transform \d+ms linear/)
  })

  it('keeps the forbidden spring/glow vocabulary out of declarations', () => {
    // Strip comments first: docs legitimately say "no spring, no shadow".
    const declarations = css.replace(/\/\*[\s\S]*?\*\//g, '')
    expect(declarations).not.toMatch(/spring|cubic-bezier|box-shadow|filter:\s*blur|scale\(1\.1\)/)
  })

  it('gives reduced-motion a static end state for new families', () => {
    const reduced = indexCss.match(
      /@media \(prefers-reduced-motion: reduce\)[\s\S]*$/
    )
    expect(reduced).not.toBeNull()
    expect(reduced[0]).toMatch(/\.toast-[a-z-]+/)
    expect(reduced[0]).toMatch(/\.stat-reveal/)
    expect(reduced[0]).toMatch(/\.list-move/)
  })
})
