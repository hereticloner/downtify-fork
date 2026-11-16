// Design-token contrast guard. The detector caught faint text at 3.7:1
// on the dark surface; this keeps the fixed token pair above WCAG AA for
// small body text without needing a browser in CI.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const css = readFileSync(join(root, 'styles/tokens.css'), 'utf8')

function block(start) {
  const i = css.indexOf(start)
  const open = css.indexOf('{', i)
  const close = css.indexOf('}', open)
  return css.slice(open + 1, close)
}
function token(source, name) {
  return source.match(new RegExp(`--c-${name}:\\s*(#[0-9a-fA-F]{6})`))?.[1]
}
function luminance(hex) {
  const ch = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const [r, g, b] = ch.map((v) =>
    v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  )
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

describe('small-text token contrast', () => {
  const themes = [
    { name: 'light', src: block(':root {'), surface: 'surface' },
    {
      name: 'dark',
      src: block(":root[data-theme='dark'] {"),
      surface: 'surface',
    },
  ]
  for (const { name, src, surface } of themes) {
    const bg = token(src, surface)
    for (const role of ['muted', 'faint']) {
      it(`${name} ${role} on surface >= 4.5:1`, () => {
        const fg = token(src, role)
        expect(fg, `${name} --c-${role} missing`).toBeTruthy()
        expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5)
      })
    }
  }
})
