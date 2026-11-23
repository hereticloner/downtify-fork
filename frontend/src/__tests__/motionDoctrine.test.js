// Motion doctrine guard v5: bans lifted. Expressive easing, glow and scale
// are allowed — what stays pinned is the structural language, the identity
// tokens, and a static reduced-motion end state (never a global kill-switch).
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const indexCss = readFileSync(join(root, 'index.css'), 'utf8')
const tokensCss = readFileSync(join(root, 'styles/tokens.css'), 'utf8')
const reduced =
  indexCss.match(/@media \(prefers-reduced-motion: reduce\)[\s\S]*$/)?.[0] || ''

describe('expressive motion doctrine', () => {
  it('keeps transform keyframes in tokens.css', () => {
    expect(tokensCss).toMatch(
      /@keyframes stagger-in[\s\S]*?transform: translateY\(10px\)/
    )
    expect(tokensCss).toMatch(
      /@keyframes stat-reveal[\s\S]*?transform: translateY\(6px\)/
    )
    expect(indexCss).not.toMatch(/@keyframes/)
  })

  it('uses springy easing on the shared entry families', () => {
    const spring = /cubic-bezier\(0\.34, 1\.4, 0\.64, 1\)/
    expect(tokensCss).toMatch(new RegExp('\\.page-enter-active[\\s\\S]*?' + spring.source))
    expect(tokensCss).toMatch(new RegExp('\\.fade-enter-active[\\s\\S]*?' + spring.source))
    expect(tokensCss).toMatch(new RegExp('\\.toast-enter-active[\\s\\S]*?' + spring.source))
    expect(indexCss).toMatch(new RegExp('\\.list-move[\\s\\S]*?' + spring.source))
  })

  it('gives play/focus states glow and press feedback scale', () => {
    expect(tokensCss).toMatch(
      /\.play-glow:hover,\s*\.play-glow:focus-visible[\s\S]*?box-shadow:/
    )
    expect(tokensCss).toMatch(
      /\.play-glow:hover,\s*\.play-glow:focus-visible[\s\S]*?scale\(1\.05\)/
    )
    expect(tokensCss).toMatch(/button:not\(:disabled\):hover[\s\S]*?scale\(1\.02\)/)
    expect(tokensCss).toMatch(/button:not\(:disabled\):active[\s\S]*?scale\(1\.04\)/)
    expect(tokensCss).toMatch(/:focus-visible[\s\S]*?box-shadow:/)
  })

  it('keeps the pinned identity tokens untouched', () => {
    expect(tokensCss).toMatch(/--c-bg: #f3f3f0;/)
    expect(tokensCss).toMatch(/--c-text: #171717;/)
    expect(tokensCss).toMatch(/--c-accent: #0047ff;/)
    expect(tokensCss).toMatch(/--radius-control: 0px;/)
  })

  it('does not globally collapse reduced-motion durations', () => {
    expect(tokensCss).not.toMatch(/animation-duration:\s*1ms\s*!important/)
    expect(indexCss).not.toMatch(/animation-duration:\s*1ms\s*!important/)
    expect(reduced).not.toBe('')
    expect(reduced).toMatch(
      /\.stagger > \*,\s*\.stagger-fade > \* \{\s*animation: none;\s*opacity: 1;\s*transform: none;/
    )
    expect(reduced).toMatch(/\.stat-reveal[\s\S]*?animation: none;[\s\S]*?transform: none;/)
    expect(reduced).toMatch(/\.play-glow[\s\S]*?box-shadow: none;/)
    expect(reduced).toMatch(
      /button:not\(:disabled\):hover,\s*button:not\(:disabled\):active \{\s*transform: none;/
    )
  })
})
