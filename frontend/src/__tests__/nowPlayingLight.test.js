// Drift guard for the Now playing light theme.
//
// NowPlaying.vue and the panels it hosts are written with hardcoded dark
// styling (`bg-[#07080b]`, `text-white/70`, ...). The light look lives in
// `src/styles/nowPlayingLight.css`, scoped under `.np-stage`. This test
// fails when a new hardcoded utility is added to the stage subtree without
// a light override - the same "parity" idea as i18nParity.test.js.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const read = (rel) => readFileSync(join(root, rel), 'utf8')

const css = read('styles/nowPlayingLight.css')
const shell = read('components/shell/NowPlaying.vue')
const panelFiles = [
  'components/player/EqualizerPanel.vue',
  'components/player/LyricsPanel.vue',
  'components/player/UpNextPanel.vue',
  'components/player/TrackDetails.vue',
  'components/player/WaveSeekBar.vue',
]
const panels = panelFiles.map(read)
const indexCss = read('index.css')

// Every hardcoded utility inside the stage subtree ...
const TOKEN =
  /(hover:|group-hover:|group-focus-visible:|focus-visible:)?((?:bg|text|border|ring|ring-offset)-(?:white(?:\/\d+)?|black(?:\/\d+)?)|from-black(?:\/\d+)?|text-\[#0b0c0e\])/g

// ... except the ones covered as a unit, not per utility:
// - the backdrop gradient (`from-black/...`) is replaced whole by `.np-veil`
// - `text-[#0b0c0e]` (icon on the white play button / active phone tab) is
//   recolored through the `.now-playing-play` / `.np-mbtn-on` hooks
// - utilities on a line mentioning `isLight` already branch in JS
//   (eyebrow `!text-white/55`)
const WHOLE_EXEMPT = new Set(['text-[#0b0c0e]'])
const isExemptToken = (token) =>
  WHOLE_EXEMPT.has(token) || token.startsWith('from-black')

function stageTokens(source) {
  const found = new Map()
  for (const line of source.split('\n')) {
    if (line.includes('isLight')) continue
    for (const match of line.matchAll(TOKEN)) {
      const token = match[0]
      if (isExemptToken(token)) continue
      if (!found.has(token)) found.set(token, line.trim().slice(0, 100))
    }
  }
  return found
}

const esc = (token) =>
  token
    .replace(/:/g, '\\:')
    .replace(/\//g, '\\/')
    .replace(/\[/g, '\\[')
    .replace(/\]/g, '\\]')

describe('now playing light theme coverage', () => {
  it('is loaded by the app stylesheet', () => {
    expect(indexCss).toContain('nowPlayingLight.css')
  })

  it('scopes every rule to the light theme inside the stage', () => {
    const scopes = css.match(/:root\[data-theme='light'\] \.np-stage/g) || []
    expect(scopes.length).toBeGreaterThan(20)
    expect(css).not.toContain("data-theme='dark'")
  })

  it('keeps the dark defaults in the template', () => {
    expect(shell).toContain('bg-[#07080b]')
    expect(shell).toContain('np-stage')
  })

  it('wires the theme and the structural hooks', () => {
    for (const hook of [
      'np-stage',
      'np-veil',
      'np-art',
      'np-mbtn-on',
      'np-vol',
      'useTheme',
      'isLight',
      'now-playing-play',
    ]) {
      expect(shell, `missing hook: ${hook}`).toContain(hook)
    }
  })

  it('recolors the tint wash in JS for light mode', () => {
    expect(shell).toContain('color-mix')
  })

  it.each([
    ['NowPlaying.vue', shell],
    ...panelFiles.map((f, i) => [f, panels[i]]),
  ])('covers every hardcoded utility in %s', (_name, source) => {
    for (const [token, line] of stageTokens(source)) {
      expect(
        css,
        `no light override for \`${token}\` (near: ${line})`
      ).toContain(`.${esc(token)}`)
    }
  })
})
