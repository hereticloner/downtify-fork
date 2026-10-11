// Shared rule for the small rename dialogs (paired apps, collections):
// a draft is worth submitting only when it is non-empty, different from
// the current name, and nothing is already saving.

export function canSubmitRename(currentName, draft, busy = false) {
  const next = String(draft || '').trim()
  return Boolean(next) && next !== String(currentName || '') && !busy
}
