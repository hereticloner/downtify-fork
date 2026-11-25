export const CATEGORY_KEYS = [
  'missing_file',
  'path_mismatch',
  'stale_mapping',
  'missing_metadata',
  'orphan_record',
]

export function categoryCounts(report) {
  const counts = Object.fromEntries(CATEGORY_KEYS.map((key) => [key, 0]))
  for (const finding of report?.findings || []) {
    if (finding.category in counts) counts[finding.category] += 1
  }
  return counts
}

export function filterFindings(findings, category) {
  const rows = Array.isArray(findings) ? findings : []
  if (!category || category === 'all') return rows
  return rows.filter((finding) => finding.category === category)
}
