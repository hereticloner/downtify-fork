import { describe, expect, it } from 'vitest'
import {
  backupRestoreRequest,
  canRestoreBackup,
  formatBackupDate,
  formatBackupSize,
} from '../lib/backupSettings'

describe('backup settings form', () => {
  it('requires a dry-run before a confirmed restore', () => {
    expect(canRestoreBackup(null)).toBe(false)
    expect(canRestoreBackup({ dry_run: true })).toBe(false)
    expect(canRestoreBackup({ dry_run: false, name: 'backup.json.gz' })).toBe(
      true
    )
  })

  it('builds separate preview and confirmed restore requests', () => {
    expect(backupRestoreRequest('backup.json.gz', true, true)).toEqual({
      name: 'backup.json.gz',
      dry_run: true,
      requeue_missing: true,
    })
    expect(backupRestoreRequest('backup.json.gz', false, true)).toEqual({
      name: 'backup.json.gz',
      dry_run: false,
      confirm: true,
      requeue_missing: true,
    })
  })

  it('formats sizes and dates without assuming a locale', () => {
    expect(formatBackupSize(0)).toBe('0 B')
    expect(formatBackupSize(1024)).toBe('1.0 KB')
    expect(formatBackupDate(0)).toMatch(/1970/)
  })
})
