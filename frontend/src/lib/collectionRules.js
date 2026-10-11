// Smart-collection rules, as the API stores them (see
// downtify/collection_rules.py). The engine lives on the server; this
// module only shapes the draft rows the editor holds and strips the
// pieces the API can't evaluate, so a half-filled row is never sent.
//
// Rule types and their fields:
//   added  — from/to dates (YYYY-MM-DD), at least one
//   plays  — min/max total play count, at least one
//   genre | artist | album | format — one value
// Rules combine with AND; there is no OR on purpose (keep it simple).

export const RULE_TYPES = [
  'added',
  'plays',
  'genre',
  'artist',
  'album',
  'format',
]

/** A fresh, empty draft row for a rule type. */
export function blankRule(type = 'genre') {
  if (type === 'added') return { type, from: '', to: '' }
  if (type === 'plays') return { type, min: '', max: '' }
  return { type, value: '' }
}

function toInt(raw) {
  const text = String(raw ?? '').trim()
  if (!text) return null
  const value = Number(text)
  return Number.isInteger(value) ? value : null
}

/** One saved rule, or `null` when the row is incomplete. */
export function cleanRule(rule) {
  if (!rule || !RULE_TYPES.includes(rule.type)) return null
  if (rule.type === 'added') {
    const from = String(rule.from || '').trim()
    const to = String(rule.to || '').trim()
    return from || to ? { type: 'added', from, to } : null
  }
  if (rule.type === 'plays') {
    const min = toInt(rule.min)
    const max = toInt(rule.max)
    if (min === null && max === null) return null
    if (min !== null && max !== null && min > max) return null
    return { type: 'plays', min, max }
  }
  const value = String(rule.value || '').trim()
  return value ? { type: rule.type, value } : null
}

/** The rule list to send to the API (incomplete rows dropped). */
export function cleanRules(rules) {
  return (rules || []).map(cleanRule).filter(Boolean)
}
