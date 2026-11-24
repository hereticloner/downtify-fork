export const QUEUE_PRIORITIES = ['normal', 'high']
const BULK_ACTIONS = ['remove', 'pause', 'resume']

export function blankQueueControl() {
  return {
    quiet_hours: {
      enabled: false,
      start: '22:00',
      end: '08:00',
      timezone: 'Europe/Istanbul',
    },
  }
}

export function mergeQueueControl(value) {
  const defaults = blankQueueControl()
  const quiet = value?.quiet_hours
  return {
    quiet_hours: {
      ...defaults.quiet_hours,
      ...(quiet && typeof quiet === 'object' ? quiet : {}),
    },
  }
}

function queueId(item) {
  return String(item?.key || item?.song?.song_id || item?.song?.url || '')
}

function uniqueIds(items) {
  return [
    ...new Set(
      (items || []).map((item) =>
        typeof item === 'string' ? item : queueId(item)
      )
    ),
  ].filter(Boolean)
}

export function selectableQueueIds(items) {
  return uniqueIds((items || []).filter((item) => item?.state === 'queued'))
}

export function sortQueueItems(items) {
  return [...(items || [])]
    .map((item, index) => ({ item, index }))
    .sort((a, b) => {
      const priority =
        Number(b.item.priority === 'high') - Number(a.item.priority === 'high')
      return priority || a.index - b.index
    })
    .map(({ item }) => item)
}

export function queuePriorityRequest(songIds, priority) {
  if (!QUEUE_PRIORITIES.includes(priority)) throw new Error('Invalid priority')
  return { song_ids: uniqueIds(songIds || []), priority }
}

export function queueBulkRequest(action, songIds) {
  if (!BULK_ACTIONS.includes(action)) throw new Error('Invalid queue action')
  return { action, song_ids: uniqueIds(songIds || []) }
}
