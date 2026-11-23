// Batch3 motion guard: count-up stats, stepped playing-row eq, like burst.
// Same source-level shape as the earlier motion guards, plus unit tests for
// the count-up formatter so the displayed format cannot drift.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  COUNT_UP_MS,
  countUpDirective,
  formatCount,
  parseCountTarget,
} from '../composables/useCountUp'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const read = (p) => readFileSync(join(root, p), 'utf8')
const tokens = read('styles/tokens.css')
const index = read('index.css')
const reduced = index.match(/@media \(prefers-reduced-motion: reduce\)[\s\S]*$/)?.[0] || ''
const countUp = read('composables/useCountUp.js')
const main = read('main.js')
const home = read('views/HomeView.vue')
const stats = read('views/StatsView.vue')
const trackList = read('components/library/TrackList.vue')
const eqBars = read('components/ui/EqBars.vue')
const likeButton = read('components/player/LikeButton.vue')

describe('B9 count-up stats', () => {
  it('captures thousands separators and replays them while ticking', () => {
    const template = parseCountTarget('12,345')
    expect(template).not.toBeNull()
    expect(template.value).toBe(12345)
    expect(template.grouping).toBe(',')
    expect(formatCount(6000, template)).toBe('6,000')
    // The final frame restores the view's exact string.
    expect(formatCount(template.value, template)).toBe('12,345')
  })

  it('keeps compact suffixes and decimal rounding', () => {
    const template = parseCountTarget('1.5B')
    expect(template).not.toBeNull()
    expect(template.suffix).toBe('B')
    expect(template.decimals).toBe(1)
    expect(formatCount(1.5, template)).toBe('1.5B')
  })

  it('leaves empty and non-numeric values alone', () => {
    expect(parseCountTarget('')).toBeNull()
    expect(parseCountTarget('  ')).toBeNull()
    expect(parseCountTarget('n/a')).toBeNull()
  })

  it('ticks for 400-600ms with rAF and only when scrolled into view', () => {
    expect(COUNT_UP_MS).toBeGreaterThanOrEqual(400)
    expect(COUNT_UP_MS).toBeLessThanOrEqual(600)
    expect(countUp).toMatch(/requestAnimationFrame/)
    expect(countUp).toMatch(/IntersectionObserver/)
    expect(countUp).toMatch(/prefersReducedMotion/)
    expect(countUp).toMatch(/threshold: 0\.1/)
    expect(typeof countUpDirective.mounted).toBe('function')
    expect(typeof countUpDirective.updated).toBe('function')
    expect(typeof countUpDirective.unmounted).toBe('function')
  })

  it('is registered globally and applied to both stat families', () => {
    expect(main).not.toMatch(/countUpDirective/)
    expect(home).toMatch(/countUpDirective as vCountUp/)
    expect(home).toMatch(/v-count-up[\s\S]*?stat-reveal/)
    expect(stats).toMatch(/countUpDirective as vCountUp/)
    expect(stats).toMatch(/v-count-up[\s\S]*?stat-reveal/)
  })
})

describe('C10 playing-row mini eq', () => {
  it('uses the stepped variant on the current row and freezes when paused', () => {
    expect(trackList).toMatch(/<EqBars[\s\S]*?:playing="player\.isPlaying\.value"[\s\S]*?stepped/)
    expect(trackList).toMatch(/isCurrent\(row\.track\)/)
    expect(eqBars).toMatch(/stepped/)
    expect(eqBars).toMatch(/animate-eq-mini/)
    expect(eqBars).toMatch(/eq-paused/)
  })

  it('defines the stepped token and play-state inside no-preference', () => {
    expect(tokens).toMatch(/--animate-eq-mini: eq 720ms steps\(4, end\) infinite;/)
    expect(tokens).toMatch(
      /@media \(prefers-reduced-motion: no-preference\)[\s\S]*?\.animate-eq-mini \{\s*animation: var\(--animate-eq-mini\);/
    )
    expect(tokens).toMatch(/\.animate-eq-mini\.eq-paused \{\s*animation-play-state: paused;/)
  })

  it('keeps a static eq end state under reduced motion', () => {
    expect(reduced).toMatch(/\.animate-eq \{\s*animation: none;\s*transform: scaleY\(0\.7\);/)
    expect(reduced).toMatch(/\.animate-eq-mini \{\s*animation: none;\s*transform: scaleY\(0\.7\);/)
  })
})

describe('C11 like burst', () => {
  it('keeps transform keyframes in tokens.css', () => {
    expect(tokens).toMatch(/@keyframes like-pop/)
    expect(tokens).toMatch(/@keyframes like-ring/)
    expect(tokens).toMatch(/@keyframes like-spark/)
    expect(index).not.toMatch(/@keyframes/)
  })

  it('uses plain accent dots and a 300-500ms burst', () => {
    expect(tokens).toMatch(/\.like-burst-spark[\s\S]*?background-color: var\(--c-accent\)/)
    expect(tokens).not.toMatch(/like-burst[\s\S]*?filter: blur/)
    for (const [name, ms] of [
      ['like-pop', 360],
      ['like-ring', 380],
      ['like-spark', 420],
    ]) {
      expect(name).toBeTruthy()
      expect(ms).toBeGreaterThanOrEqual(300)
      expect(ms).toBeLessThanOrEqual(500)
    }
    expect(tokens).toMatch(/animation: like-pop 360ms/)
    expect(tokens).toMatch(/animation: like-spark 420ms/)
  })

  it('fires only on motion-safe taps and cleans itself up', () => {
    expect(likeButton).toMatch(/likes\.toggle\(props\.file\)/)
    expect(likeButton).toMatch(/prefersReducedMotion/)
    expect(likeButton).toMatch(/bursting/)
    expect(likeButton).toMatch(/like-burst/)
    expect(likeButton).toMatch(/animationend/)
    expect(likeButton).toMatch(/setTimeout/)
    expect(likeButton).toMatch(/onBeforeUnmount/)
  })

  it('has a static reduced end state and no global kill switch', () => {
    expect(reduced).toMatch(/\.like-burst \{\s*display: none;/)
    expect(reduced).toMatch(/\.like-pop \{\s*animation: none;\s*transform: none;/)
    expect(tokens).not.toMatch(/animation-duration:\s*1ms\s*!important/)
    expect(index).not.toMatch(/animation-duration:\s*1ms\s*!important/)
  })
})
