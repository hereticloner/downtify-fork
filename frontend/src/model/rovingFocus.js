// Roving-tabindex keyboard navigation for a list of rows.
//
// The whole list is a single Tab stop: the row at `active` has `tabindex="0"`
// and every other row `tabindex="-1"`. Arrow keys move the stop (and, when a
// DOM focus callback is given, the real focus) so a keyboard user can walk the
// list, play a song with Enter / Space, or open its action menu with the
// Context Menu key / Shift+F10 — all without the global shortcuts also firing.
import { ref, unref } from 'vue'

/**
 * Maps a keydown to an intent, or `null` when the key is not ours.
 * Kept separate from the composable so it can be unit-tested as a table.
 */
export function resolveRovingKey(event) {
  switch (event.key) {
    case 'ArrowDown':
      return { type: 'move', delta: 1 }
    case 'ArrowUp':
      return { type: 'move', delta: -1 }
    case 'Home':
      return { type: 'edge', edge: 'start' }
    case 'End':
      return { type: 'edge', edge: 'end' }
    case 'Enter':
    case ' ':
      return { type: 'activate' }
    case 'ContextMenu':
      return { type: 'menu' }
    case 'F10':
      return event.shiftKey ? { type: 'menu' } : null
    default:
      return null
  }
}

/**
 * @param {object} options
 * @param {number|Function} options.count Number of rows (a getter is fine).
 * @param {(index: number) => void} [options.onActivate] Enter / Space handler.
 * @param {(index: number, event: KeyboardEvent) => void} [options.onMenu]
 *   Context Menu / Shift+F10 handler.
 * @param {(index: number) => void} [options.onFocus] Called with the newly
 *   active index after a keyboard move, so the component can move real focus.
 */
export function useRovingFocus({ count, onActivate, onMenu, onFocus } = {}) {
  const active = ref(0)

  function length() {
    const value = typeof count === 'function' ? count() : unref(count)
    return Number.isFinite(value) ? value : 0
  }

  function setActive(index, { focus = false } = {}) {
    const size = length()
    if (size <= 0) return
    active.value = Math.min(Math.max(index, 0), size - 1)
    if (focus) onFocus?.(active.value)
  }

  function tabindexFor(index) {
    if (length() <= 0) return -1
    return index === active.value ? 0 : -1
  }

  function onRowKeydown(event, index) {
    // Keys pressed on the row's own controls (select, like, ⋯) belong to
    // those controls, not to the row.
    if (event.currentTarget && event.target !== event.currentTarget) {
      return false
    }
    const intent = resolveRovingKey(event)
    if (!intent) return false
    // Handled here: don't let the key bubble to the window shortcut handler,
    // where ↑/↓ would change the volume and Space would toggle playback.
    event.stopPropagation?.()
    event.preventDefault?.()
    if (intent.type === 'move') {
      setActive(active.value + intent.delta, { focus: true })
    } else if (intent.type === 'edge') {
      setActive(intent.edge === 'start' ? 0 : length() - 1, { focus: true })
    } else if (intent.type === 'activate') {
      onActivate?.(index)
    } else if (intent.type === 'menu') {
      onMenu?.(index, event)
    }
    return true
  }

  return { active, setActive, tabindexFor, onRowKeydown }
}
