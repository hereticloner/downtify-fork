import { describe, expect, it } from 'vitest'

import bg from '/src/i18n/locales/bg.js'
import el from '/src/i18n/locales/el.js'
import en from '/src/i18n/locales/en.js'
import es from '/src/i18n/locales/es.js'
import fr from '/src/i18n/locales/fr.js'
import hu from '/src/i18n/locales/hu.js'
import ptBr from '/src/i18n/locales/pt-BR.js'
import tr from '/src/i18n/locales/tr.js'

const locales = { bg, el, en, es, fr, hu, 'pt-BR': ptBr, tr }
const required = [
  'profileSubtitle',
  'archiveRange',
  'topTrack',
  'totalPlays',
  'allTime',
  'topArtists',
  'topAlbums',
  'listeningReport',
  'canonicalPlays',
  'periodSummary',
  'archiveScope',
  'sourcePriority',
  'profileEmpty',
  'hoursMinutes',
  'weekLabel',
  'track',
  'artist',
  'album',
  'source',
  'time',
  'rank',
  'initials',
  'measuredListening',
  'listeningProfile',
  'periodPlays',
  'sourceSplit',
  'uniqueTracks',
  'uniqueArtists',
  'knownAlbums',
  'knownTrackTime',
  'trackTimeHint',
  'durationCoverage',
  'historyCoverage',
  'patterns',
  'hourOfDayUtc',
  'weekdayUtc',
  'lastfmDetail',
  'lastfmLoved',
  'lastfmMbid',
  'lastfmImported',
  'lastfmImportNone',
  'lastfmImporting',
  'lastfmImportDone',
  'dayLoadFailed',
  'dayTruncated',
  'playCount',
  'heatmapKeyboardHint',
  'contextSpotifyPlaylist',
  'contextSpotifyArtist',
  'contextSpotifyAlbum',
  'patternHourTitle',
  'patternShare',
  'patternDetail',
  'patternTopTracks',
  'patternTopArtists',
  'patternRecent',
  'patternEmpty',
  'patternLoadFailed',
  'patternTruncated',
  'patternClear',
]

describe('Stats locale contract', () => {
  it.each(Object.entries(locales))(
    '%s has every Stats detail key',
    (code, messages) => {
      for (const key of required) {
        expect(messages.stats?.[key], `${code}.stats.${key}`).toBeDefined()
      }
      expect(
        messages.stats.playCount.other,
        `${code}.stats.playCount.other`
      ).toBeTypeOf('string')
    }
  )
})
