// Queue list layout: row estimates for the window virtualizer.
// 4.0 rows: compact queued/done rows are a 40px tile + py-2 inside an
// 80px block; active rows add the segmented progress line (88px).

export const QUEUE_ROW_GAP = 8

/** Estimated row height including the gap below it. */
export function queueRowEstimate(state) {
  if (state === 'failed') return 112
  if (state === 'active') return 96
  return 80 + QUEUE_ROW_GAP
}
