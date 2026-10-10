import { ref, computed, watch } from 'vue'

import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { currentLocale, t } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'
import { needsLanguageSync, splitUiLanguage } from '/src/lib/uiLanguage'

const settings = ref({
  audio_providers: ['youtube-music'],
  external_library: {
    folders: [],
  },
  lyrics_providers: [''],
  download_lyrics: true,
  lyrics_lrc_beside: true,
  lyrics_lrc_dir: '/data/lyrics',
  format: '',
  bitrate: '320',
  output: '',
  generate_m3u: true,
  download_cover_art_playlists: true,
  download_cover_art_artist: true,
  download_cover_art_artist_banner: false,
  sync_navidrome: true,
  navidrome: {
    enabled: false,
    url: '',
    username: '',
    password: '',
    admin_username: '',
    admin_password: '',
    public_playlist: false,
    scan_after_download: true,
    scan_wait_seconds: 120,
    scan_poll_seconds: 30,
    client_name: 'Downtify',
    api_version: '1.16.1',
  },
  notifications: {
    enabled: false,
    telegram_enabled: false,
    telegram_bot_token: '',
    telegram_chat_id: '',
    notify_watch_downloads: true,
  },
  scrobbling: {
    enabled: false,
    lastfm_enabled: false,
    lastfm_api_key: '',
    lastfm_api_secret: '',
    lastfm_session_key: '',
    lastfm_username: '',
    scrobble_now_playing: true,
  },
  spotify_mirror: {
    enabled: false,
    client_id: '',
    redirect_uri: '',
    device_id: '',
    access_token: '',
    refresh_token: '',
    token_expires_at: '',
    mirror_user: '',
    silent_on_target: true,
    mirror_manual_checks: false,
  },
  organize_by_artist: true,
  cache_cover_art: false,
  organize_by_album: true,
  max_parallel_downloads: 3,
  download_delay_seconds: 0,
  external_sync_delay_seconds: 0,
  cover_resolution: 600,
  download_cover_art: true,
  overwrite_existing_files: true,
  search_albums: true,
  mini_player_enabled: true,
})

const MIN_PARALLEL_DOWNLOADS = 1
const MAX_PARALLEL_DOWNLOADS = 30

const MIN_DOWNLOAD_DELAY_SECONDS = 0
const MAX_DOWNLOAD_DELAY_SECONDS = 300

const MIN_COVER_RESOLUTION = 300
const MAX_COVER_RESOLUTION = 1200

const settingsOptions = {
  audio_providers: ['youtube', 'youtube-music'],
  lyrics_providers: ['lrclib', 'genius', 'musixmatch', 'azlyrics'],
  format: ['mp3', 'flac', 'ogg', 'opus', 'm4a'],
  bitrate: ['128', '192', '256', '320'],
  max_parallel_downloads_presets: [1, 2, 3, 5, 8],
  max_parallel_downloads_min: MIN_PARALLEL_DOWNLOADS,
  max_parallel_downloads_max: MAX_PARALLEL_DOWNLOADS,
  download_delay_seconds_presets: [0, 5, 15, 30, 60],
  download_delay_seconds_min: MIN_DOWNLOAD_DELAY_SECONDS,
  download_delay_seconds_max: MAX_DOWNLOAD_DELAY_SECONDS,
  external_sync_delay_seconds_presets: [0, 5, 15, 30, 60],
  external_sync_delay_seconds_min: MIN_DOWNLOAD_DELAY_SECONDS,
  external_sync_delay_seconds_max: MAX_DOWNLOAD_DELAY_SECONDS,
  cover_resolution_presets: [300, 600, 800, 1000, 1200],
  cover_resolution_min: MIN_COVER_RESOLUTION,
  cover_resolution_max: MAX_COVER_RESOLUTION,
  output: '{artists} - {title}.{output-ext}',
}

// The browser origin for default redirect suggestions; empty when the
// module runs outside a browser (the node test environment).
let browserOrigin = ''
try {
  browserOrigin = window.location.origin
} catch {
  browserOrigin = ''
}

export function clampParallelDownloads(value) {
  const parsed = Number.parseInt(value, 10)
  if (Number.isNaN(parsed)) {
    return MIN_PARALLEL_DOWNLOADS
  }
  return Math.min(
    MAX_PARALLEL_DOWNLOADS,
    Math.max(MIN_PARALLEL_DOWNLOADS, parsed)
  )
}

export function clampDownloadDelaySeconds(value) {
  const parsed = Number.parseInt(value, 10)
  if (Number.isNaN(parsed)) {
    return MIN_DOWNLOAD_DELAY_SECONDS
  }
  return Math.min(
    MAX_DOWNLOAD_DELAY_SECONDS,
    Math.max(MIN_DOWNLOAD_DELAY_SECONDS, parsed)
  )
}

export const clampExternalSyncDelaySeconds = clampDownloadDelaySeconds

export function clampCoverResolution(value) {
  const parsed = Number.parseInt(value, 10)
  if (Number.isNaN(parsed)) {
    return MIN_COVER_RESOLUTION
  }
  return Math.min(MAX_COVER_RESOLUTION, Math.max(MIN_COVER_RESOLUTION, parsed))
}

// Last state the server confirmed — the settings page compares against
// it to show a "Save changes" bar only when something actually changed.
const saved = ref('')
const loaded = ref(false)

function snapshot() {
  return JSON.stringify(settings.value)
}

// The language the server has on file (`ui_language`). Deliberately not in
// `settings`: the settings page saves that whole object, and the language is
// owned by the language picker, not by the form.
const uiLanguage = ref('')

/**
 * Tell the server the language the page is shown in, when it doesn't have it
 * yet or has an old one. Runs on every page load - so someone who chose a
 * language before the server kept it needs to do nothing - and whenever the
 * language changes. A failure is not worth reporting: the next load or
 * change tries again.
 */
async function syncUiLanguage() {
  const code = currentLocale.value
  if (!needsLanguageSync(uiLanguage.value, code)) return
  try {
    const res = await API.setSettings({ ui_language: code })
    uiLanguage.value = splitUiLanguage(res.data).uiLanguage
  } catch {
    // Retried on the next page load or language change.
  }
}

// Server settings are an admin's: other users never load them (the
// Settings page only shows them General, Apps and About).
let requested = false

function loadServerSettings() {
  if (requested) return
  requested = true
  API.getSettings()
    .then((res) => {
      const { uiLanguage: known, rest } = splitUiLanguage(res.data)
      uiLanguage.value = known
      // Merge nested blocks over the defaults so a settings file saved
      // before Navidrome existed still binds every form field.
      settings.value = {
        ...settings.value,
        ...rest,
        navidrome: { ...settings.value.navidrome, ...(rest.navidrome || {}) },
        notifications: {
          ...settings.value.notifications,
          ...(rest.notifications || {}),
        },
        scrobbling: {
          ...settings.value.scrobbling,
          ...(rest.scrobbling || {}),
        },
        spotify_mirror: {
          ...settings.value.spotify_mirror,
          ...(rest.spotify_mirror || {}),
          redirect_uri:
            (rest.spotify_mirror || {}).redirect_uri ||
            `${browserOrigin}/integrations/spotify/callback`,
        },
        external_library: {
          ...settings.value.external_library,
          ...(rest.external_library || {}),
          folders: Array.isArray(rest.external_library?.folders)
            ? rest.external_library.folders
            : settings.value.external_library.folders,
        },
      }
      saved.value = snapshot()
      loaded.value = true
      syncUiLanguage()
    })
    .catch(() => {
      loaded.value = true
    })
}

const auth = useAuth()
watch(
  () => [auth.loaded.value, auth.isAdmin.value],
  ([ready, admin]) => {
    if (!ready) return
    if (admin) {
      loadServerSettings()
    } else {
      // Nothing of the server's to edit: never "unsaved".
      saved.value = snapshot()
      loaded.value = true
    }
  },
  { immediate: true }
)

watch(currentLocale, () => {
  if (loaded.value && auth.isAdmin.value) syncUiLanguage()
})

const dirty = computed(() => loaded.value && snapshot() !== saved.value)
const isSaved = ref()
const saving = ref(false)
// Backend rejection reason (e.g. Navidrome enabled without a password).
const saveErrorText = ref('')

function rememberExternalFolders(folders) {
  if (!Array.isArray(folders)) return
  if (!settings.value.external_library) {
    settings.value.external_library = { folders: [] }
  }
  settings.value.external_library.folders = folders
  if (!saved.value) return
  try {
    const parsed = JSON.parse(saved.value)
    parsed.external_library = {
      ...(parsed.external_library || {}),
      folders,
    }
    saved.value = JSON.stringify(parsed)
  } catch {
    /* ignore a corrupt snapshot */
  }
}

function reset() {
  if (saved.value) settings.value = JSON.parse(saved.value)
}

/** Save everything; resolves true on success. */
async function saveSettings() {
  saving.value = true
  saveErrorText.value = ''
  try {
    const res = await API.setSettings(settings.value)
    const { uiLanguage: known, rest } = splitUiLanguage(res.data)
    uiLanguage.value = known
    settings.value = {
      ...settings.value,
      ...rest,
      navidrome: { ...settings.value.navidrome, ...(rest.navidrome || {}) },
      notifications: {
        ...settings.value.notifications,
        ...(rest.notifications || {}),
      },
      scrobbling: {
        ...settings.value.scrobbling,
        ...(rest.scrobbling || {}),
      },
      spotify_mirror: {
        ...settings.value.spotify_mirror,
        ...(rest.spotify_mirror || {}),
        redirect_uri:
          (rest.spotify_mirror || {}).redirect_uri ||
          `${browserOrigin}/integrations/spotify/callback`,
      },
      external_library: {
        ...settings.value.external_library,
        ...(rest.external_library || {}),
        folders: Array.isArray(rest.external_library?.folders)
          ? rest.external_library.folders
          : settings.value.external_library.folders,
      },
    }
    saved.value = snapshot()
    isSaved.value = true
    return true
  } catch (error) {
    saveErrorText.value = friendlyError(t, error, 'errors.generic')
    isSaved.value = false
    return false
  } finally {
    saving.value = false
    setTimeout(() => {
      isSaved.value = null
    }, 3000)
  }
}

export function useSettingsManager() {
  return {
    saveSettings,
    reset,
    rememberExternalFolders,
    settings,
    settingsOptions,
    isSaved,
    saving,
    dirty,
    loaded,
    saveErrorText,
  }
}
