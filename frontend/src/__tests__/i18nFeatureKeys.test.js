import { describe, expect, it } from 'vitest'

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
}

const required = [
  'search.library',
  'search.libraryEmpty',
  'similar.downloadNew',
  'similar.downloadNewCount',
]

describe('feature translation keys', () => {
  it('exists in every locale', async () => {
    const { AVAILABLE_LOCALES, loadLocale, setLocale, t } =
      await import('../i18n')
    for (const locale of AVAILABLE_LOCALES) {
      await loadLocale(locale.code)
      setLocale(locale.code)
      for (const key of required) {
        expect(t(key), `${locale.code}: ${key}`).not.toBe(key)
      }
    }
    setLocale('en')
  })
})
