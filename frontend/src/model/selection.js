// Bulk selection for a track list, shared by the Library's Tracks tab and
// the Album / Playlist / Artist track lists. One instance per view; it
// resets whenever `resetKey` changes so a selection never leaks across
// albums, playlists, artists or library tabs.
//
// It owns both the state (the `selected` Set the TrackList binds to) and
// the bulk actions the SelectionBar fires (play / enqueue / zip / delete /
// add-to-playlist), so every view wires the same contract.
import { computed, ref, unref, watch } from 'vue'

import { useTrackActions } from '/src/model/trackActions'
import { usePlaylistActions } from '/src/model/playlistActions'

export function useTrackSelection({
  tracks,
  resetKey,
  context,
  onDeleted,
} = {}) {
  const actions = useTrackActions()
  const playlistActions = usePlaylistActions()

  const selected = ref(new Set())
  const zipping = ref(false)

  const list = computed(() => {
    const value = typeof tracks === 'function' ? tracks() : unref(tracks)
    return value || []
  })
  // The bar's count is the raw selection size (a selection made before a
  // filter changed still counts), matching the Library's Tracks tab.
  const count = computed(() => selected.value.size)
  const total = computed(() => list.value.length)
  const selectedTracks = computed(() =>
    list.value.filter((track) => selected.value.has(track.file))
  )

  function has(file) {
    return selected.value.has(file)
  }

  function toggle(file) {
    const next = new Set(selected.value)
    if (next.has(file)) next.delete(file)
    else next.add(file)
    selected.value = next
  }

  function selectAll() {
    selected.value = new Set(list.value.map((track) => track.file))
  }

  function toggleAll() {
    if (count.value > 0 && count.value === total.value) clear()
    else selectAll()
  }

  function drop(files) {
    const gone = new Set(files)
    selected.value = new Set(
      [...selected.value].filter((file) => !gone.has(file))
    )
  }

  function clear() {
    selected.value = new Set()
  }

  function ctx() {
    return typeof context === 'function' ? context() : unref(context)
  }

  function playSelected() {
    actions.play(selectedTracks.value, 0, ctx())
  }

  function enqueueSelected() {
    actions.enqueue(selectedTracks.value)
  }

  async function zipSelected() {
    if (!selectedTracks.value.length) return
    zipping.value = true
    try {
      await actions.downloadZip(selectedTracks.value)
    } finally {
      zipping.value = false
    }
  }

  async function deleteSelected() {
    const deleted = await actions.remove(selectedTracks.value)
    if (deleted.length) {
      drop(deleted)
      onDeleted?.(deleted)
    }
    return deleted
  }

  function addSelectedToPlaylist() {
    playlistActions.openCreate(selectedTracks.value)
  }

  if (resetKey !== undefined) watch(resetKey, clear)

  return {
    selected,
    count,
    total,
    zipping,
    selectedTracks,
    has,
    toggle,
    toggleAll,
    selectAll,
    clear,
    drop,
    playSelected,
    enqueueSelected,
    zipSelected,
    deleteSelected,
    addSelectedToPlaylist,
  }
}
