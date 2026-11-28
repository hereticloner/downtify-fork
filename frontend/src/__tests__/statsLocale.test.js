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

describe('Stats two-source copy', () => {
  it.each(Object.entries(locales))(
    '%s describes only Downtify and Last.fm as Stats sources',
    (code, messages) => {
      const priority = messages.stats?.sourcePriority || ''
      expect(priority, `${code}.stats.sourcePriority`).not.toContain('Spotify')
      expect(priority, `${code}.stats.sourcePriority`).toContain(
        'Downtify → Last.fm'
      )
    }
  )

  const importHints = {
    en: 'Store your Spotify listening history separately every half hour. Stats uses Last.fm + Downtify. Needs one reconnect so Spotify grants the scope.',
    tr: 'Spotify dinleme geçmişini her yarım saatte ayrı olarak sakla. Stats Last.fm + Downtify kullanır. Spotify’in izni vermesi için bir kez yeniden bağlantı gerekir.',
    es: 'Guarda tu historial de escuchas de Spotify por separado cada media hora. Stats usa Last.fm + Downtify. Requiere una reconexión para que Spotify conceda el permiso.',
    fr: 'Enregistrez séparément votre historique d’écoute Spotify toutes les demi-heures. Stats utilise Last.fm + Downtify. Une reconnexion est nécessaire pour que Spotify accorde l’autorisation.',
    'pt-BR':
      'Salve seu histórico de reproduções do Spotify separadamente a cada meia hora. As estatísticas usam Last.fm + Downtify. É necessário reconectar para o Spotify conceder a permissão.',
    hu: 'A Spotify hallgatási előzményeit félóránként külön tárolja. A Stats a Last.fm + Downtify forrásait használja. A Spotify engedélyezéséhez egyszeri újracsatlakozás szükséges.',
    el: 'Αποθηκεύστε χωριστά το ιστορικό ακρόασης Spotify κάθε μισή ώρα. Τα Stats χρησιμοποιούν Last.fm + Downtify. Απαιτείται μια επανασύνδεση για να παραχωρήσει άδεια το Spotify.',
    bg: 'Запазва историята на слушането в Spotify отделно на всеки половин час. Stats използва Last.fm + Downtify. Нужно е еднократно повторно свързване, за да разреши Spotify.',
  }

  it.each(Object.entries(locales))(
    '%s keeps Spotify history separate from Stats',
    (code, messages) => {
      expect(
        messages.settings?.spotifyMirrorImportHint,
        `${code}.settings.spotifyMirrorImportHint`
      ).toBe(importHints[code])
    }
  )
})
