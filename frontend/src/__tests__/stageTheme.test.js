// Neon stage theme + global press feedback drift guard.
//
// The whole app recolors through `styles/tokens.css`, and every button
// answers a press through the base rules in `index.css` (`scale` while
// held) plus the `.pressable` wave on the shared controls. This test
// fails when a token is dropped or a shared control loses its feedback.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const read = (rel) => readFileSync(join(root, rel), 'utf8')

const tokens = read('styles/tokens.css')
const indexCss = read('index.css')
const iconButton = read('components/ui/UiIconButton.vue')
const uiButton = read('components/ui/UiButton.vue')
const miniPlayer = read('components/shell/MiniPlayer.vue')
const nowPlaying = read('components/shell/NowPlaying.vue')

describe('neon stage tokens', () => {
  it('defines glow shadows for both themes', () => {
    for (const token of ['--sh-glow:', '--sh-glow-lg:', '--shadow-glow:']) {
      expect(tokens).toContain(token)
    }
    expect(tokens.match(/--sh-glow-lg:/g)?.length).toBe(2)
  })

  it('uses the neon accent, not the old green', () => {
    expect(tokens).toContain('#a855f7')
    expect(tokens).not.toContain('#1ad05c')
    expect(tokens).not.toContain('#22e584')
  })

  it('deepens the dark stage surfaces', () => {
    expect(tokens).toContain('--c-bg: #060709')
  })
})

describe('global press feedback', () => {
  it('shrinks every held button and restores it', () => {
    expect(indexCss).toContain('button:not(:disabled):active')
    expect(indexCss).toContain('scale: 0.94')
  })

  it('blooms a wave while the press lands', () => {
    expect(indexCss).toContain('.pressable:active::after')
    expect(indexCss).toContain('@keyframes press-wave')
  })

  it('leaves reduced-motion users still', () => {
    const reduced = indexCss.slice(indexCss.indexOf('prefers-reduced-motion'))
    expect(reduced).toContain('scale: 1')
    expect(indexCss).toContain('press-wave 450ms')
  })
})

describe('shared controls carry feedback', () => {
  it('waves on every icon and text button', () => {
    expect(iconButton).toContain('pressable')
    expect(uiButton).toContain('pressable')
  })

  it('glows on primary actions and play buttons', () => {
    expect(uiButton).toContain('shadow-glow')
    expect(miniPlayer).toContain('shadow-glow')
    expect(nowPlaying).toContain('shadow-glow')
  })
})
