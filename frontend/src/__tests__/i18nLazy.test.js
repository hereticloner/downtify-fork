// Lazy locale guard. The initial bundle should ship English (the
// fallback) and fetch the other seven only when selected. i18nParity
// checks the messages themselves; this checks the loading strategy.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { AVAILABLE_LOCALES, loadLocale, setLocale, t } from '../i18n'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const source = readFileSync(join(root, 'i18n/index.js'), 'utf8')

describe('lazy locales', () => {
  it('statically imports only the fallback locale', () => {
    const staticImports =
      source.match(/^import \w+ from '\.\/locales\/.+'$/gm) || []
    expect(staticImports).toHaveLength(1)
    expect(staticImports[0]).toContain('en.js')
  })

  it('registers a dynamic loader for every other locale', () => {
    for (const { code, load } of AVAILABLE_LOCALES) {
      expect(typeof load, code).toBe('function')
    }
    const dynamic = source.match(/import\('\.\/locales\/[^']+'\)/g) || []
    expect(dynamic).toHaveLength(AVAILABLE_LOCALES.length - 1)
  })

  it('keeps t() synchronous and falls back while a chunk loads', async () => {
    // Switching the locale is synchronous for callers: the promise is
    // only for tests that want to assert the loaded text immediately.
    const promise = setLocale('tr')
    // Not loaded yet: English still answers, never a missing key.
    expect(t('common.tracks', { count: 3 })).toBe('3 tracks')
    await promise
    expect(t('common.tracks', { count: 3 })).toBe('3 parça')
    const messages = await loadLocale('tr')
    expect(messages.language.name.length).toBeGreaterThan(0)
    await setLocale('en')
  })
})
