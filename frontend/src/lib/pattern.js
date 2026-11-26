/** Resolve a one-dimensional pattern-chart key into a clamped intent. */
export function resolvePatternKey(event, index, count) {
  const size = Math.max(0, Number(count) || 0)
  if (!size) return null
  const current = Math.min(Math.max(Number(index) || 0, 0), size - 1)
  switch (event?.key) {
    case 'ArrowRight':
      return { type: 'move', index: Math.min(current + 1, size - 1) }
    case 'ArrowLeft':
      return { type: 'move', index: Math.max(current - 1, 0) }
    case 'Home':
      return { type: 'edge', index: 0 }
    case 'End':
      return { type: 'edge', index: size - 1 }
    case 'Enter':
    case ' ':
      return { type: 'activate', index: current }
    default:
      return null
  }
}

export function patternPercent(count, total) {
  const value = Number(count) || 0
  const sum = Number(total) || 0
  return sum > 0 ? (value / sum) * 100 : 0
}
