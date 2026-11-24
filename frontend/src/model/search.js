// Free-text search across YouTube Music songs, albums and artists.
import { ref } from 'vue'

import API from '/src/model/api'
import { useAccount } from '/src/model/account'
import { useLibrary } from '/src/model/library'
import { mergeSearchResults } from '/src/lib/searchMerge'
import { t } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'

const query = ref('')
const localTracks = ref([])
const songs = ref([])
const albums = ref([])
const artists = ref([])
const loading = ref(false)
const error = ref('')
let serial = 0

async function searchFor(text) {
  const term = String(text || '').trim()
  query.value = term
  if (!term) {
    localTracks.value = []
    songs.value = []
    albums.value = []
    artists.value = []
    return
  }
  const mine = ++serial
  loading.value = true
  error.value = ''
  // The signed-in user's own choice (Settings > General).
  const withAlbums = useAccount().searchAlbums.value !== false
  // Albums and artists are extras: their failure never hides songs.
  const [localRes, songRes, albumRes, artistRes] = await Promise.allSettled([
    useLibrary().searchTracks(term, { limit: 50 }),
    API.search(term),
    withAlbums ? API.searchAlbums(term) : Promise.resolve({ data: [] }),
    API.searchArtists(term),
  ])
  if (mine !== serial) return
  localTracks.value =
    localRes.status === 'fulfilled' ? localRes.value || [] : []
  if (songRes.status === 'fulfilled') {
    songs.value = mergeSearchResults(
      localTracks.value,
      songRes.value.data || []
    ).tracks
  } else {
    songs.value = []
    error.value = friendlyError(t, songRes.reason, 'search.failed')
  }
  albums.value =
    albumRes.status === 'fulfilled' ? albumRes.value.data || [] : []
  artists.value =
    artistRes.status === 'fulfilled' ? artistRes.value.data || [] : []
  loading.value = false
}

export function useSearch() {
  return {
    query,
    localTracks,
    songs,
    albums,
    artists,
    loading,
    error,
    searchFor,
  }
}
