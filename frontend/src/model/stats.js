// The Stats tab's numbers: what /api/stats knows about the library, the
// downloads and what has been played. Module state like the other stores,
// so the page and every panel read the same answer.
import { ref } from 'vue'

import API from '/src/model/api'

const stats = ref({})
const loading = ref(true)
const error = ref(false)
const dayLoading = ref(false)
const dayError = ref(false)
const patternLoading = ref(false)
const patternError = ref(false)
const selectedPattern = ref(null)
const days = ref(30)
let requestSequence = 0

function emptyPattern() {
  return {
    kind: '',
    bucket: null,
    total: 0,
    by_source: { downtify: 0, spotify: 0, lastfm: 0 },
    top_tracks: [],
    top_artists: [],
    recent: [],
    truncated: false,
  }
}

function mergeDetail(incoming, field) {
  const playback = stats.value.playback || {}
  const nextPlayback = { ...playback }
  if (incoming?.playback?.[field] !== undefined) {
    nextPlayback[field] = incoming.playback[field]
  }
  if (incoming?.playback?.context_labels) {
    nextPlayback.context_labels = {
      ...(playback.context_labels || {}),
      ...incoming.playback.context_labels,
    }
  }
  stats.value = { ...stats.value, playback: nextPlayback }
}

export function playsForDay(value, selectedDate) {
  const playback = value?.playback || {}
  if (!selectedDate) return playback.recent || []
  return playback.day?.date === selectedDate ? playback.day.plays || [] : []
}

async function load(selectedDate = '', { background = false } = {}) {
  const request = ++requestSequence
  if (background) {
    dayLoading.value = true
    dayError.value = false
  } else {
    loading.value = true
    error.value = false
    dayLoading.value = false
    dayError.value = false
    patternLoading.value = false
    patternError.value = false
  }
  const params = { days: days.value, scope: 'user' }
  if (selectedDate) params.date = selectedDate
  if (!background && selectedPattern.value) {
    params.pattern = selectedPattern.value.kind
    params.bucket = selectedPattern.value.bucket
  }
  try {
    const res = await API.getStats(params)
    if (request !== requestSequence) return
    if (background) mergeDetail(res.data, 'day')
    else stats.value = res.data
  } catch {
    if (request !== requestSequence) return
    if (background) dayError.value = true
    else error.value = true
  } finally {
    if (request === requestSequence) {
      loading.value = false
      dayLoading.value = false
      patternLoading.value = false
    }
  }
}

async function loadPattern(kind, bucket) {
  const request = ++requestSequence
  selectedPattern.value = { kind, bucket }
  patternLoading.value = true
  patternError.value = false
  try {
    const res = await API.getStats({
      days: days.value,
      scope: 'user',
      pattern: kind,
      bucket,
    })
    if (request === requestSequence) mergeDetail(res.data, 'pattern_detail')
  } catch {
    if (request === requestSequence) patternError.value = true
  } finally {
    if (request === requestSequence) {
      loading.value = false
      dayLoading.value = false
      patternLoading.value = false
    }
  }
}

function clearPattern() {
  requestSequence += 1
  selectedPattern.value = null
  patternLoading.value = false
  patternError.value = false
  const playback = stats.value.playback || {}
  stats.value = {
    ...stats.value,
    playback: { ...playback, pattern_detail: emptyPattern() },
  }
}

/** The Stats tab's data, plus the `load` the page calls on mount. */
export function useStats() {
  return {
    stats,
    loading,
    error,
    dayLoading,
    dayError,
    patternLoading,
    patternError,
    selectedPattern,
    days,
    load,
    loadPattern,
    clearPattern,
  }
}
