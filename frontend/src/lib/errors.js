// Turn an axios/network error into a localized, user-safe message.
//
// The backend sends machine-readable codes next to its English `detail`
// text (see downtify/errors.py); `friendlyError` translates the code and
// NEVER returns the raw `detail` or `err.message`. Codes with no known
// translation fall back to a generic message.

/**
 * Known backend error code → i18n key. A code missing here is still tried
 * as `errors.<code>` before the generic fallback, but keeping the known
 * ones in one place makes the mapping testable. See
 * frontend/src/i18n/locales/*.js for the matching strings.
 */
export const ERROR_KEYS = {
  'auth.disabled': 'errors.auth.disabled',
  'auth.forbidden': 'errors.auth.forbidden',
  'auth.invalid_credentials': 'errors.auth.invalid_credentials',
  'auth.not_ready': 'errors.auth.not_ready',
  'auth.pairing_code': 'errors.auth.pairing_code',
  'auth.pairing_not_found': 'errors.auth.pairing_not_found',
  'auth.rate_limited': 'errors.auth.rate_limited',
  'auth.signin_required': 'errors.auth.signin_required',
  'download.failed': 'errors.download.failed',
  'download.no_songs': 'errors.download.no_songs',
  'download.not_ready': 'errors.download.not_ready',
  'podcast.feed_error': 'errors.podcast.feed_error',
  'request.conflict': 'errors.request.conflict',
  'request.invalid': 'errors.request.invalid',
  'request.invalid_url': 'errors.request.invalid_url',
  'request.missing_field': 'errors.request.missing_field',
  'request.too_large': 'errors.request.too_large',
  'request.unsupported_url': 'errors.request.unsupported_url',
  'resource.not_found': 'errors.resource.not_found',
  'server.error': 'errors.server.error',
  'server.port_in_use': 'errors.server.port_in_use',
  'server.port_locked': 'errors.server.port_locked',
  'server.starting': 'errors.server.starting',
  'spotify.not_connected': 'errors.spotify.not_connected',
}

/** `t` returns the key itself when a message is missing. */
function missing(t, key) {
  return t(key) === key
}

/**
 * A localized message for *err*, safe to show the user.
 *
 * @param {Function} t i18n translator
 * @param {unknown} err the caught axios/network error
 * @param {string} [fallbackKey] i18n key for a response with no code
 * @returns {string}
 */
export function friendlyError(t, err, fallbackKey) {
  if (!err) return t('errors.unknown')
  const code = err?.response?.data?.code
  if (typeof code === 'string' && code) {
    const key = ERROR_KEYS[code] || `errors.${code}`
    if (!missing(t, key)) return t(key)
    return t('errors.generic')
  }
  if (!err?.response) return t('errors.network')
  return fallbackKey ? t(fallbackKey) : t('errors.generic')
}

export default friendlyError
