import { describe, expect, it } from 'vitest'

/**
 * Structural parity gate for the i18n locale files.
 *
 * The locale set is discovered from disk rather than from the runtime
 * registry, so a new file cannot escape the gate by forgetting to
 * register it in `src/i18n/index.js`. `en.js` is the reference: every
 * other locale must expose exactly the same key paths, and every value
 * must carry a real translation.
 */

const localeModules = import.meta.glob('../i18n/locales/*.js', {
  eager: true,
  import: 'default',
})

const LOCALES = Object.keys(localeModules)
  .sort()
  .map((path) => ({
    code: path.split('/').pop().replace(/\.js$/, ''),
    messages: localeModules[path],
  }))

/**
 * The languages the app ships. Adding one means: create the locale
 * file, register it in `src/i18n/index.js`, and extend this list.
 */
const EXPECTED_CODES = ['bg', 'el', 'en', 'es', 'fr', 'hu', 'pt-BR', 'tr']

const REFERENCE = 'en'

/**
 * The registry is imported defensively. A deleted or renamed locale
 * file breaks `src/i18n/index.js`, and a static import would take the
 * whole suite down with a stack trace instead of a readable failure.
 */
const registry = await (async () => {
  try {
    const mod = await import('../i18n')
    return { locales: mod.AVAILABLE_LOCALES, error: null }
  } catch (error) {
    return { locales: [], error }
  }
})()

/**
 * Flatten a message tree into `{'a.b': '…'}` leaves. Plural forms
 * (`{ one, other }`) contribute one path per form.
 */
function flatten(obj, prefix = '', out = {}) {
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value !== null && typeof value === 'object') flatten(value, path, out)
    else out[path] = value
  }
  return out
}

/** Paths of message groups that hold no entries at all. */
function emptyGroups(obj, prefix = '', out = []) {
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value !== null && typeof value === 'object') {
      if (Object.keys(value).length === 0) out.push(path)
      else emptyGroups(value, path, out)
    }
  }
  return out
}

const reference = LOCALES.find((locale) => locale.code === REFERENCE)
const referenceKeys = reference
  ? Object.keys(flatten(reference.messages)).sort()
  : []

describe('i18n locale files', () => {
  it('has an en.js reference locale', () => {
    expect(
      reference,
      `src/i18n/locales/${REFERENCE}.js is missing`
    ).toBeDefined()
  })

  it('ships exactly the expected set of locale files', () => {
    expect(
      LOCALES.map((locale) => locale.code),
      'locale files found in src/i18n/locales'
    ).toEqual(EXPECTED_CODES)
  })

  it('loads the runtime registry', () => {
    expect(
      registry.error,
      `src/i18n/index.js failed to load: ${registry.error}`
    ).toBeNull()
  })

  it('registers every locale file in the runtime registry', () => {
    const registered = new Map(
      registry.locales.map((locale) => [locale.code, locale.messages])
    )
    for (const { code, messages } of LOCALES) {
      expect(
        registered.has(code),
        `${code}: not registered in AVAILABLE_LOCALES (src/i18n/index.js)`
      ).toBe(true)
      expect(
        registered.get(code),
        `${code}: registry entry does not point at locales/${code}.js`
      ).toBe(messages)
    }
  })
})

for (const { code, messages } of LOCALES) {
  describe(`locale ${code}`, () => {
    const flat = flatten(messages)
    const keys = Object.keys(flat).sort()

    it('has exactly the same keys as en.js', () => {
      const missing = referenceKeys.filter((key) => !keys.includes(key))
      const extra = keys.filter((key) => !referenceKeys.includes(key))

      expect(
        missing,
        `${code}: missing key(s) present in en.js: ${missing.join(', ')}`
      ).toEqual([])
      expect(
        extra,
        `${code}: key(s) absent from en.js: ${extra.join(', ')}`
      ).toEqual([])
    })

    it('has no empty translations', () => {
      const empty = keys.filter(
        (key) => typeof flat[key] === 'string' && flat[key].trim() === ''
      )
      expect(
        empty,
        `${code}: empty or whitespace-only value(s): ${empty.join(', ')}`
      ).toEqual([])
    })

    it('has only string values', () => {
      const invalid = keys.filter((key) => typeof flat[key] !== 'string')
      expect(
        invalid,
        `${code}: non-string value(s): ${invalid.join(', ')}`
      ).toEqual([])
    })

    it('has no empty message groups', () => {
      const empty = emptyGroups(messages)
      expect(
        empty,
        `${code}: message group(s) without entries: ${empty.join(', ')}`
      ).toEqual([])
    })
  })
}
