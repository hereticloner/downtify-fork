// B9 — count-up stats. A tiny directive: read the text the view already
// formatted, then tick 0 -> target when the node scrolls into view. The exact
// original string is restored on the last frame, so the view's own formatter
// (thousands separator, rounding, compact suffix) always wins. Non-numeric
// and empty values are left untouched, and reduced motion skips entirely.

import { prefersReducedMotion } from '../lib/viewTransitions'

export const COUNT_UP_MS = 500

/**
 * Capture a formatted number as a reusable template.
 *   '12,345' -> { prefix:'', grouping:',', decimal:'', decimals:0, suffix:'', value:12345 }
 *   '1.5B'   -> { ..., decimal:'.', decimals:1, suffix:'B', value:1.5 }
 * Returns null for empty / non-numeric / NaN text.
 */
export function parseCountTarget(text) {
  const source = String(text ?? '').trim()
  const match = /^([^0-9+-]*)([+-]?[0-9][0-9.,]*)(.*)$/.exec(source)
  if (!match) return null
  const [, prefix, token, suffix] = match
  const sign = token.startsWith('-') ? -1 : 1
  const digits = token.replace(/^[+-]/, '')
  const commas = digits.split(',').length - 1
  const dots = digits.split('.').length - 1
  const tailAfter = (sep) => digits.split(sep)[1].length

  // One separator with 1-2 trailing digits is decimal; three digits (or a
  // repeated separator) is grouping. Both present: the rightmost is decimal.
  let decimal = ''
  if (commas && dots) {
    decimal = digits.lastIndexOf(',') > digits.lastIndexOf('.') ? ',' : '.'
  } else if (commas === 1 && tailAfter(',') <= 2) {
    decimal = ','
  } else if (dots === 1 && tailAfter('.') <= 2) {
    decimal = '.'
  }
  const grouping = [',', '.'].find((sep) => sep !== decimal && digits.includes(sep))
    || (decimal ? '' : [',', '.'].find((sep) => digits.includes(sep)))
    || ''

  const decimalAt = decimal ? digits.lastIndexOf(decimal) : -1
  const intPart = decimalAt >= 0 ? digits.slice(0, decimalAt) : digits
  const fracPart = decimalAt >= 0 ? digits.slice(decimalAt + 1) : ''
  const clean = grouping ? intPart.split(grouping).join('') : intPart
  const value = Number(`${sign < 0 ? '-' : ''}${clean}.${fracPart || '0'}`)
  if (!Number.isFinite(value)) return null
  return { prefix, suffix, grouping, decimal, decimals: fracPart.length, value }
}

/** Render `value` through a captured template, rounding like the target did. */
export function formatCount(value, template) {
  if (!template) return ''
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  const fixed = Math.abs(n).toFixed(template.decimals)
  const [int, frac] = fixed.split('.')
  const grouped = template.grouping
    ? int.replace(/\B(?=(\d{3})+(?!\d))/g, template.grouping)
    : int
  const number = `${n < 0 ? '-' : ''}${grouped}${frac ? template.decimal + frac : ''}`
  return `${template.prefix}${number}${template.suffix}`
}

const states = new WeakMap()

export const countUpDirective = {
  mounted(el, binding) {
    const target = el.textContent.trim()
    const template = parseCountTarget(target)
    // Empty, NaN or reduced motion: keep the node exactly as the view wrote it.
    if (!template || prefersReducedMotion()) return
    // A numeric binding slows (or speeds) this one site up without touching
    // the shared default; garbage falls back to COUNT_UP_MS.
    const requested = Number(binding?.value)
    const duration = Number.isFinite(requested) && requested > 0 ? requested : COUNT_UP_MS
    const entry = { target, template, duration, done: false, frame: 0, observer: null }
    states.set(el, entry)

    const start = () => {
      if (entry.done || entry.frame) return
      const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
      const tick = (now) => {
        const p = Math.min(1, ((now ?? Date.now()) - t0) / entry.duration)
        const out = 1 - (1 - p) * (1 - p) // simple out, no spring
        el.textContent = formatCount(entry.template.value * out, entry.template)
        if (p < 1) {
          entry.frame = requestAnimationFrame(tick)
        } else {
          entry.frame = 0
          entry.done = true
          el.textContent = entry.target // exact formatter output wins
        }
      }
      entry.frame = requestAnimationFrame(tick)
    }

    if (typeof IntersectionObserver === 'undefined') {
      start()
      return
    }
    entry.observer = new IntersectionObserver(
      (records) => {
        if (!records.some((record) => record.isIntersecting)) return
        entry.observer.disconnect()
        entry.observer = null
        start()
      },
      { threshold: 0.1 }
    )
    entry.observer.observe(el)
  },

  updated(el) {
    const entry = states.get(el)
    if (!entry) return
    const target = el.textContent.trim()
    const template = parseCountTarget(target)
    if (!template) return
    // Async stats load after mount: refresh the template without replaying an
    // already finished animation (Vue has written the correct final text).
    entry.target = target
    entry.template = template
  },

  unmounted(el) {
    const entry = states.get(el)
    if (!entry) return
    if (entry.frame) cancelAnimationFrame(entry.frame)
    if (entry.observer) entry.observer.disconnect()
    states.delete(el)
  },
}
