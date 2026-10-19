import { describe, expect, it } from 'vitest'
import {
  CHECK_DONE_PHASES,
  applyCheckEvent,
  checkToast,
  isChecking,
} from '../lib/monitorCheck.js'
import { t } from '../i18n'

// The Monitor page's "Şimdi kontrol et" click: it drops a local stub into
// the row straight away (MonitorView.startCheck), then the server's
// `monitor_check` events take over. These tests feed the same events the
// server broadcasts (downtify/monitor.py: check_watch) through that state
// machine and check what the row ends up showing.
const LOCAL_STUB = {
  phase: 'progress',
  done: 0,
  total: null,
  name: 'Road Trip',
  startedAt: 1_700_000_000_000,
  local: true,
}

const stubbed = { 2: { ...LOCAL_STUB } }

const event = (phase, extra = {}) => ({
  type: 'monitor_check',
  phase,
  id: 2,
  name: 'Road Trip',
  kind: 'playlist',
  ...extra,
})

// What the watcher in the view would toast for this state, if it hasn't
// already announced it.
const toastFor = (state) => checkToast(t, state[2])

describe('a check that starts', () => {
  // The bug this guards: `start` fell through to the unknown-phase branch
  // and every manual check toasted "Bir şeyler ters gitti" the moment it
  // began, then toasted the real result 30 seconds later.
  it('lands in the running phase, never in error', () => {
    const next = applyCheckEvent(stubbed, event('start'))
    expect(next[2].phase).toBe('progress')
    expect(next[2].phase).not.toBe('error')
    expect(isChecking(next[2])).toBe(true)
    expect(toastFor(next)).toBeNull()
  })

  it('replaces the click stub but keeps the row it started on', () => {
    const next = applyCheckEvent(stubbed, event('start'))
    expect(next[2].local).toBeUndefined()
    expect(next[2].done).toBe(0)
    expect(next[2].total).toBeNull()
    expect(next[2].name).toBe('Road Trip')
    expect(next[2].startedAt).toBe(LOCAL_STUB.startedAt)
  })

  it('opens a row that had no stub (a sweep Downtify started itself)', () => {
    const next = applyCheckEvent({}, event('start'), 1_700_000_005_000)
    expect(next[2]).toEqual({
      phase: 'progress',
      done: 0,
      total: null,
      name: 'Road Trip',
      startedAt: 1_700_000_005_000,
    })
    expect(toastFor(next)).toBeNull()
  })
})

describe('a check that runs', () => {
  it('follows the sweep with done/total', () => {
    const running = applyCheckEvent(
      stubbed,
      event('progress', {
        done: 3,
        total: 7,
      })
    )
    expect(running[2]).toMatchObject({ phase: 'progress', done: 3, total: 7 })
    expect(toastFor(running)).toBeNull()
  })

  it('leaves other rows alone', () => {
    const other = { 9: { ...LOCAL_STUB, name: 'Kitchen' } }
    const next = applyCheckEvent(other, event('progress', { done: 1 }))
    expect(next[9]).toEqual(other[9])
    expect(Object.keys(next).sort()).toEqual(['2', '9'])
  })
})

describe('a check that finishes', () => {
  it('names the count downloaded and closes the row', () => {
    const next = applyCheckEvent(stubbed, event('end', { downloaded: 4 }))
    expect(next[2].phase).toBe('end')
    expect(toastFor(next)).toEqual({
      text: '4 new tracks downloaded',
      kind: 'info',
    })
    expect(CHECK_DONE_PHASES).toContain(next[2].phase)
  })
})

describe('a check that fails', () => {
  it('reports the reason the server sent', () => {
    const next = applyCheckEvent(
      stubbed,
      event('error', { message: 'Rate limited by the source' })
    )
    expect(next[2].phase).toBe('error')
    expect(toastFor(next)).toEqual({
      text: 'Check failed: Rate limited by the source',
      kind: 'error',
    })
    expect(CHECK_DONE_PHASES).toContain(next[2].phase)
  })

  it('falls back to the generic toast when there is no reason', () => {
    // An older server sends a bare `error`.
    const next = applyCheckEvent(stubbed, event('error'))
    expect(toastFor(next)).toEqual({
      text: 'Something went wrong',
      kind: 'error',
    })
  })

  it('treats a phase this build does not know as a failure', () => {
    const next = applyCheckEvent(stubbed, event('something-new'))
    expect(next[2].phase).toBe('error')
    expect(toastFor(next).kind).toBe('error')
  })
})

describe('messages that are not check events', () => {
  it.each([
    ['another type', { type: 'queue', phase: 'start', id: 2 }],
    ['no id', { type: 'monitor_check', phase: 'start' }],
    ['nothing', null],
  ])('leaves the state untouched (%s)', (_label, data) => {
    expect(applyCheckEvent(stubbed, data)).toBe(stubbed)
  })
})
