// Reordering the Up-next queue from the keyboard or with buttons.
//
// Dragging already works with a pointer. These helpers add the same
// move for keyboards (Alt + arrow keys on a row) and feed the visible
// up/down buttons, so neither needs a mouse.

/**
 * Maps a row keydown to a move direction (+1 down, -1 up), or `null`
 * when the key isn't ours. Alt keeps it clear of the global arrow-key
 * volume shortcuts.
 */
export function resolveReorderKey(event) {
  if (!event.altKey) return null
  if (event.key === 'ArrowUp') return -1
  if (event.key === 'ArrowDown') return 1
  return null
}

/**
 * Where a row at `index` lands when moved one step in `direction`, or
 * `null` at an edge so the button can stay disabled and the key ignored.
 * `min`/`max` bound the allowed destinations — the first queued track
 * sits just after the current one, so it can never move above it.
 */
export function reorderTarget(
  index,
  direction,
  { min = 0, max = Infinity } = {}
) {
  const to = index + direction
  if (to < min || to > max) return null
  return to
}

/**
 * Wires the reorder intent to a `moveTrack(from, to)`-style callback.
 * `min`/`max` are getters so they follow the playing index and the
 * queue length.
 */
export function createQueueReorder({
  onMove,
  min = () => 0,
  max = () => Infinity,
}) {
  function canMove(index, direction) {
    return reorderTarget(index, direction, { min: min(), max: max() }) !== null
  }

  function move(index, direction) {
    const to = reorderTarget(index, direction, { min: min(), max: max() })
    if (to === null) return false
    onMove(index, to)
    return true
  }

  function onRowKeydown(event, index) {
    const direction = resolveReorderKey(event)
    if (direction === null) return false
    // Own the key so the global shortcuts don't also see the arrow.
    event.preventDefault?.()
    event.stopPropagation?.()
    return move(index, direction)
  }

  return { canMove, move, onRowKeydown }
}
