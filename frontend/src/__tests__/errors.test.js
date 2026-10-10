import { afterEach, describe, expect, it } from 'vitest'
import { setLocale, t } from '../i18n'
import { ERROR_KEYS, friendlyError } from '../lib/errors'

/** An axios-like error carrying a backend machine code. */
function coded(code, detail = 'RAW BACKEND DETAIL') {
  return { response: { status: 400, data: { detail, code } } }
}

describe('friendlyError', () => {
  afterEach(() => setLocale('en'))

  it('translates a known backend code', () => {
    expect(friendlyError(t, coded('auth.invalid_credentials'), 'x.foo')).toBe(
      'Wrong username or password.'
    )
  })

  it('translates another known code (rate limited)', () => {
    expect(friendlyError(t, coded('auth.rate_limited'), 'x.foo')).toBe(
      'Too many attempts. Wait a few minutes and try again.'
    )
  })

  it('falls back to generic for an unknown code', () => {
    expect(friendlyError(t, coded('no.such.code'), 'x.foo')).toBe(
      'Something went wrong. Please try again.'
    )
  })

  it('treats a response-less error as a network error', () => {
    expect(friendlyError(t, { message: 'Network Error' }, 'x.foo')).toBe(
      t('errors.network')
    )
    expect(
      friendlyError(t, { code: 'ERR_NETWORK', message: 'x' }, 'x.foo')
    ).toBe(t('errors.network'))
    expect(friendlyError(t, { message: 'Failed to fetch' }, 'x.foo')).toBe(
      t('errors.network')
    )
  })

  it('uses the fallback key when the response has no code', () => {
    const err = { response: { status: 500, data: { detail: 'Raw' } } }
    expect(friendlyError(t, err, 'toast.actionFailed')).toBe(
      'Something went wrong'
    )
  })

  it('uses generic when there is no fallback key either', () => {
    const err = { response: { status: 500, data: { detail: 'Raw' } } }
    expect(friendlyError(t, err)).toBe(t('errors.generic'))
  })

  it('returns unknown for a missing error', () => {
    expect(friendlyError(t, null, 'x.foo')).toBe(t('errors.unknown'))
    expect(friendlyError(t, undefined, 'x.foo')).toBe(t('errors.unknown'))
  })

  it('never returns the raw backend detail or err.message', () => {
    const err = {
      message: 'Request failed with status code 500',
      response: { status: 500, data: { detail: 'ENGLISH BACKEND TEXT' } },
    }
    const shown = friendlyError(t, err, 'toast.actionFailed')
    expect(shown).toBe('Something went wrong')
    expect(shown).not.toContain('ENGLISH BACKEND TEXT')
    expect(shown).not.toContain('Request failed')

    const codedErr = coded('auth.invalid_credentials', 'RAW SECRET')
    const codedShown = friendlyError(t, codedErr, 'toast.actionFailed')
    expect(codedShown).not.toContain('RAW SECRET')

    const network = friendlyError(
      t,
      { message: 'ENGLISH NETWORK' },
      'toast.actionFailed'
    )
    expect(network).not.toContain('ENGLISH NETWORK')
  })
})

describe('ERROR_KEYS', () => {
  it('maps every key to an existing error message', () => {
    for (const [code, key] of Object.entries(ERROR_KEYS)) {
      expect(key, code).toBe(`errors.${code}`)
      expect(t(key), `${code} has no message`).not.toBe(key)
    }
  })
})
