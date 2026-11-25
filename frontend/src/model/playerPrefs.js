// Player display preferences. Remembered in this browser, like the theme,
// and kept with the signed-in account (see model/account.js).
import { useLocalStorage } from '@vueuse/core'
import { v4 as uuidv4 } from 'uuid'

// Only hides the lyrics; the files keep the ones Downtify embedded, and
// "Download lyrics" (a server setting) is untouched.
const showLyrics = useLocalStorage('downtify-show-lyrics', true)
const lyricsDeviceId = useLocalStorage('downtify-lyrics-device-id', uuidv4())
const lyricsOffset = useLocalStorage('downtify-lyrics-offset', 0)

export function usePlayerPrefs() {
  return { showLyrics, lyricsDeviceId, lyricsOffset }
}
