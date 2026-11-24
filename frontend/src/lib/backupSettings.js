export function canRestoreBackup(preview) {
  return Boolean(preview?.dry_run === false && preview?.name)
}

export function backupRestoreRequest(name, dryRun, requeueMissing) {
  return {
    name,
    dry_run: dryRun,
    ...(dryRun ? {} : { confirm: true }),
    requeue_missing: requeueMissing,
  }
}

export function formatBackupSize(bytes) {
  const value = Number(bytes) || 0
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

export function formatBackupDate(timestamp) {
  return new Date(Number(timestamp) * 1000)
    .toISOString()
    .replace('T', ' ')
    .slice(0, 19)
}
