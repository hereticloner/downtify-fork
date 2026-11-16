// Selection helpers for the Monitor watch table. Pure, so the bulk
// behavior is testable without mounting the view. IDs are numbers.

export function toggleId(selected, id) {
  const next = new Set(selected)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  return next
}

export function selectMany(selected, ids) {
  const next = new Set(selected)
  for (const id of ids) next.add(id)
  return next
}

export function clearSelection() {
  return new Set()
}

/** Keep only IDs still present (e.g. after a watch was deleted). */
export function pruneSelection(selected, ids) {
  const live = new Set(ids)
  return new Set([...selected].filter((id) => live.has(id)))
}

/**
 * Shift-range selection: add every id between `anchor` and `id` in the
 * currently visible order, keeping the rest of the selection.
 */
export function selectRange(selected, visibleIds, anchor, id) {
  const a = visibleIds.indexOf(anchor)
  const b = visibleIds.indexOf(id)
  if (a < 0 || b < 0) return selectMany(selected, [id])
  const ordered =
    a <= b ? visibleIds.slice(a, b + 1) : visibleIds.slice(b, a + 1).reverse()
  return selectMany(selected, ordered)
}

export function selectedItems(items, selected) {
  return items.filter((item) => selected.has(item.id))
}
