import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

import ListeningPatterns from '/src/components/library/ListeningPatterns.vue'
import { resolvePatternKey } from '/src/lib/pattern'

async function render(props) {
  const app = createSSRApp({ render: () => h(ListeningPatterns, props) })
  return renderToString(app)
}

describe('resolvePatternKey', () => {
  it('moves horizontally and clamps at the edges', () => {
    expect(resolvePatternKey({ key: 'ArrowRight' }, 0, 24)).toEqual({
      type: 'move',
      index: 1,
    })
    expect(resolvePatternKey({ key: 'ArrowLeft' }, 0, 24)).toEqual({
      type: 'move',
      index: 0,
    })
    expect(resolvePatternKey({ key: 'End' }, 0, 24)).toEqual({
      type: 'edge',
      index: 23,
    })
  })

  it('supports Home, activation and ignores unrelated keys', () => {
    expect(resolvePatternKey({ key: 'Home' }, 10, 24)).toEqual({
      type: 'edge',
      index: 0,
    })
    expect(resolvePatternKey({ key: 'Enter' }, 10, 24)).toEqual({
      type: 'activate',
      index: 10,
    })
    expect(resolvePatternKey({ key: 'Escape' }, 10, 24)).toBeNull()
    expect(resolvePatternKey({ key: 'ArrowRight' }, 10, 0)).toBeNull()
  })
})

describe('ListeningPatterns', () => {
  it('renders real buttons with one tab stop per chart', async () => {
    const html = await render({
      hours: Array.from({ length: 24 }, (_, index) => index),
      weekdays: Array.from({ length: 7 }, (_, index) => index),
      selected: { kind: 'hour', bucket: 14 },
      periodTotal: 100,
      locale: 'en',
    })

    expect(html.match(/tabindex="0"/g) || []).toHaveLength(2)
    expect(html.match(/tabindex="-1"/g) || []).toHaveLength(29)
    expect(html.match(/aria-pressed="true"/g) || []).toHaveLength(1)
    expect(html).toContain('outline-accent')
    expect(html).not.toContain('role="img"')
  })

  it('declares tooltip, coarse-pointer and reduced-motion contracts', () => {
    const source = readFileSync(
      new URL('../components/library/ListeningPatterns.vue', import.meta.url),
      'utf8'
    )

    expect(source).toContain('role="tooltip"')
    expect(source).toContain('aria-describedby')
    expect(source).toContain('pointer: coarse')
    expect(source).toContain('prefers-reduced-motion')
  })
})
