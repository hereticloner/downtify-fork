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
    'NotificationsPanel.vue'
  ),
  'utf8'
)

describe('NotificationsPanel client render', () => {
  it('compiles with channel forms and event checkboxes', () => {
    const { descriptor } = parse(source)
    expect(() =>
      compileScript(descriptor, {
        id: 'notifications-panel-client',
        inlineTemplate: true,
      })
    ).not.toThrow()
    expect(source).toContain('type="password"')
    expect(source).toContain('type="checkbox"')
    expect(source).toContain('config.channels[eventChannel].events')
    expect(source).toContain('notificationEventsFor')
  })
})
