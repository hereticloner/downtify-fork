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
  'settings.ntfyEnabled',
  'settings.ntfyEnabledHint',
  'settings.ntfyUrl',
  'settings.ntfyUrlHint',
  'settings.ntfyToken',
  'settings.ntfyTokenHint',
  'settings.webhookEnabled',
  'settings.webhookEnabledHint',
  'settings.webhookUrl',
  'settings.webhookUrlHint',
  'settings.webhookToken',
  'settings.webhookTokenHint',
  'settings.notificationSecretSaved',
  'settings.notificationEvents',
  'settings.notificationEventsHint',
  'settings.notificationEventsFor',
  'settings.notifyDownloadCompleted',
  'settings.notifyDownloadFailed',
  'settings.notifyDownloadBatch',
  'settings.notifyUpgradeStarted',
  'settings.notifyUpgradeFinished',
  'settings.notifyUpgradeFailed',
  'settings.notifyBackupCompleted',
  'settings.notifyBackupFailed',
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
