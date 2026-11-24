import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse, compileScript } from '@vue/compiler-sfc'

const source = readFileSync(
  join(
    dirname(fileURLToPath(import.meta.url)),
    '..',
    'components',
    'settings',
    'BackupPanel.vue'
  ),
  'utf8'
)

describe('BackupPanel client render', () => {
  it('compiles with preview, confirmation and upload controls', () => {
    const { descriptor } = parse(source)
    expect(() =>
      compileScript(descriptor, {
        id: 'backup-panel-client',
        inlineTemplate: true,
      })
    ).not.toThrow()
    expect(source).toContain('backupSecretWarning')
    expect(source).toContain('backupRestoreRequest')
    expect(source).toContain('type="file"')
    expect(source).toContain('canRestoreBackup')
  })
})
