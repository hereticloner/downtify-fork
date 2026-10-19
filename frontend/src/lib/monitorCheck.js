// The Playlist Monitor's live check state, as a pure state machine over
// the server's `monitor_check` WebSocket events (downtify/monitor.py:
// `check_watch`).
//
// A check opens with `start`, ticks once per track with `progress` and
// closes with `end` (how many were downloaded) or `error` (why it gave
// up). `start` is the START of a check, not a failure of one, so it
// lands in the same `progress` phase the click's local stub does — the
// only phases that close a row are `end`/`error`, and a phase this build
// doesn't know is treated as an error rather than a row that never ends.

/** Phases that close a row; the caller drops the entry after a beat. */
export const CHECK_DONE_PHASES = ['end', 'error']

/** True while the row's check is still running. */
export function isChecking(state) {
  return state?.phase === 'progress'
}

/**
 * The next check state for a `monitor_check` event: watch id -> {phase,
 * done, total, startedAt, name, downloaded, message}.
 *
 * Returns `state` untouched for anything that isn't one of ours, so a
 * caller can skip its side effects (the row reload, the cleanup timer)
 * by comparing the result with what it passed in.
 *
 * @param {Record<string, object>} state current state, by watch id
 * @param {unknown} data the WebSocket payload
 * @param {number} [now] ms clock, for an event on a row with no stub
 * @returns {Record<string, object>} the next state
 */
export function applyCheckEvent(state, data, now = Date.now()) {
  if (!data || data.type !== 'monitor_check' || data.id == null) return state
  const prev = state[data.id] || {}
  const base = {
    name: data.name ?? prev.name,
    startedAt: prev.startedAt || now,
  }
  const put = (entry) => ({ ...state, [data.id]: { ...base, ...entry } })
  if (data.phase === 'start') {
    return put({ phase: 'progress', done: 0, total: null })
  }
  if (data.phase === 'progress') {
    return put({
      phase: 'progress',
      done: data.done ?? 0,
      total: data.total ?? null,
    })
  }
  if (data.phase === 'end') {
    return put({ phase: 'end', downloaded: data.downloaded ?? 0 })
  }
  return put({ phase: 'error', message: data.message || '' })
}

/**
 * The one toast a check state calls for, or null while it runs: the
 * count when it finished, the reason when it failed (older servers send
 * no `message`, so those keep the generic wording).
 *
 * @param {Function} t i18n translator
 * @param {object} st an entry from the check state
 * @returns {{ text: string, kind: string } | null}
 */
export function checkToast(t, st) {
  if (!st) return null
  if (st.phase === 'end') {
    return {
      text: t('monitor.checkFinished', { count: st.downloaded ?? 0 }),
      kind: 'info',
    }
  }
  if (st.phase === 'error') {
    return {
      text: st.message
        ? t('monitor.checkErrorReason', { reason: st.message })
        : t('toast.actionFailed'),
      kind: 'error',
    }
  }
  return null
}
