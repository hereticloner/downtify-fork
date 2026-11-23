// Batch2 motion guard: cursor trail, route progress bar and View Transitions.
// Source-level checks keep the same shape as the other motion guards.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const read = (p) => readFileSync(join(root, p), 'utf8')
const tokens = read('styles/tokens.css')
const index = read('index.css')
const shell = read('components/shell/AppShell.vue')
const trail = read('components/shell/CursorTrail.vue')
const progress = read('composables/useRouteProgress.js')
const vt = read('lib/viewTransitions.js')
const main = read('main.js')
const reduced =
  index.match(/@media \(prefers-reduced-motion: reduce\)[\s\S]*$/)?.[0] || ''

describe('batch2 motion', () => {
  it('A5 renders a fine-pointer, motion-safe trail that touch/reduced never see', () => {
    expect(shell).toMatch(/<CursorTrail \/>/)
    expect(trail).toMatch(
      /\(hover: hover\) and \(pointer: fine\) and \(prefers-reduced-motion: no-preference\)/
    )
    expect(trail).toMatch(/v-if="enabled"/)
    expect(trail).toMatch(/pointermove/)
    expect(trail).toMatch(/transitionDuration/)
    expect(reduced).toMatch(/\.cursor-trail/)
  })

  it('B6 drives a 2px accent bar below the masthead from router guards', () => {
    expect(progress).toMatch(/router\.beforeEach/)
    expect(progress).toMatch(/router\.afterEach/)
    expect(main).toMatch(/installRouteProgress\(router\)/)
    expect(shell).toMatch(/<Transition name="progress">/)
    expect(shell).toMatch(/route-progress/)
    expect(tokens).toMatch(/\.route-progress[\s\S]*?height: 2px/)
    expect(tokens).toMatch(
      /@media \(prefers-reduced-motion: no-preference\)[\s\S]*?\.route-progress-fill/
    )
    expect(reduced).toMatch(/\.route-progress \{\s*display: none;/)
  })

  it('B7 feature-detects startViewTransition and skips it under reduced motion', () => {
    expect(vt).toMatch(/document\.startViewTransition/)
    expect(vt).toMatch(/prefersReducedMotion\(\)/)
    expect(vt).toMatch(/to\.path === from\.path/)
    expect(vt).toMatch(/nextTick/)
    expect(main).toMatch(/installViewTransitions\(router\)/)
    expect(shell).toMatch(
      /supportsViewTransitions\(\) && !prefersReducedMotion\(\)/
    )
    expect(shell).toMatch(/route-view-root/)
    expect(tokens).toMatch(/view-transition-name: route-content/)
  })

  it('keeps the no-global-kill-switch and keyframe-location doctrine', () => {
    expect(index).not.toMatch(/@keyframes/)
    expect(tokens).not.toMatch(/animation-duration:\s*1ms\s*!important/)
    expect(index).not.toMatch(/animation-duration:\s*1ms\s*!important/)
  })
})
