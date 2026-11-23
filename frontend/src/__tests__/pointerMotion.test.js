// Pointer-reactive motion guard: the new hover/pointer transforms are gated
// to fine pointers without reduced motion, and reduced motion is static.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const read = (p) => readFileSync(join(root, p), 'utf8')
const tokens = read('styles/tokens.css')
const index = read('index.css')
const cover = read('components/ui/CoverArt.vue')
const button = read('components/ui/UiButton.vue')
const chips = read('components/ui/UiChips.vue')
const tabs = read('components/ui/UiTabs.vue')
const sw = read('components/ui/UiSwitch.vue')
const reduced = index.match(/@media \(prefers-reduced-motion: reduce\)[\s\S]*$/)?.[0] || ''

describe('pointer-reactive motion', () => {
  it('writes cover parallax props from pointer handlers and gates the transform', () => {
    expect(cover).toMatch(/@pointermove="onPointerMove"/)
    expect(cover).toMatch(/@pointerleave="onPointerLeave"/)
    expect(cover).toMatch(/--px/)
    expect(tokens).toMatch(
      /@media \(hover: hover\) and \(prefers-reduced-motion: no-preference\)[\s\S]*?\.cover-parallax[\s\S]*?translate\(var\(--px, 0px\), var\(--py, 0px\)\)/
    )
  })

  it('drifts primary buttons via translate so the shared hover scale survives', () => {
    expect(button).toMatch(/btn-magnetic/)
    expect(button).toMatch(/--mx/)
    expect(tokens).toMatch(/\.btn-magnetic \{\s*translate: var\(--mx, 0px\) var\(--my, 0px\);\s*\}/)
  })

  it('has a motion-safe accent sweep on primary buttons and active chips', () => {
    expect(button).toMatch(/btn-sweep/)
    expect(chips).toMatch(/btn-sweep/)
    expect(tokens).toMatch(/\.btn-sweep:hover::after/)
    expect(tokens).toMatch(/background-position: 100% 0/)
    expect(tokens).toMatch(/linear-gradient\(/)
  })

  it('slides the tab marker and switch tick with a static reduced end state', () => {
    expect(tabs).toMatch(/tab-indicator/)
    expect(sw).toMatch(/switch-knob/)
    expect(tokens).toMatch(/\.tab-indicator \{[\s\S]*?transform 200ms/)
    expect(tokens).toMatch(/\.switch-knob-enter-from[\s\S]*?translateX\(-8px\)/)
    expect(reduced).toMatch(/\.tab-indicator \{\s*transition: none;/)
    expect(reduced).toMatch(
      /\.switch-knob-enter-from,\s*\.switch-knob-leave-to \{\s*opacity: 1;\s*transform: none;/
    )
  })

  it('never introduces a global reduced-motion kill switch', () => {
    expect(tokens).not.toMatch(/animation-duration:\s*1ms\s*!important/)
    expect(index).not.toMatch(/animation-duration:\s*1ms\s*!important/)
  })
})
