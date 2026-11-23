// Motion doctrine guard: keeps the pinned v4 motion language from drifting
// back into spring/slide territory. Mirrors tokenContrast.test.js style.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const indexCss = readFileSync(join(root, 'index.css'), 'utf8')
const tokensCss = readFileSync(join(root, 'styles/tokens.css'), 'utf8')

describe('diagnostic motion doctrine', () => {
  it('keeps list transitions short, stepped and opacity-only', () => {
    expect(indexCss).not.toMatch(/180ms ease-out/)
    expect(indexCss).not.toMatch(/translateY/)
    expect(indexCss).toMatch(
      /\.list-enter-active[\s\S]*?opacity 100ms steps\(3, end\)/
    )
  })

  it('keeps page and fade transitions stepped', () => {
    expect(
      tokensCss.match(/transition: opacity 100ms steps\(3, end\)/g)
    ).toHaveLength(2)
  })

  it('gives buttons opacity-only press feedback', () => {
    expect(tokensCss).toMatch(
      /button:not\(:disabled\):active \{\s*opacity: 0\.6;/
    )
  })

  it('does not globally collapse reduced-motion durations', () => {
    expect(tokensCss).not.toMatch(/animation-duration:\s*1ms\s*!important/)
    expect(indexCss).toMatch(/@media \(prefers-reduced-motion: reduce\)/)
    expect(indexCss).toMatch(/\.animate-eq[\s\S]*?animation: none/)
  })
})
