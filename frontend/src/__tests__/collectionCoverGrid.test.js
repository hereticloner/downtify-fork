import { describe, expect, it } from 'vitest'

// i18n/CoverArt read a few browser globals at import time; a minimal
// shim keeps the SSR render in Node without a browser.
globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
}
globalThis.window = {
  location: {
    protocol: 'http:',
    host: 'localhost:8000',
    origin: 'http://localhost:8000',
  },
  matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  innerWidth: 1200,
  innerHeight: 900,
  addEventListener: () => {},
  removeEventListener: () => {},
}
globalThis.document = {
  documentElement: { setAttribute: () => {}, style: {} },
  createElement: () => ({ style: {} }),
  querySelector: () => null,
  addEventListener: () => {},
  removeEventListener: () => {},
}

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import CoverArt from '/src/components/ui/CoverArt.vue'

async function render(props) {
  const app = createSSRApp({ render: () => h(CoverArt, props) })
  const ctx = {}
  return renderToString(app, ctx)
}

const cover = (n) => `/cover?file=${n}.mp3`

describe('CoverArt mosaic grid', () => {
  it('draws a single cover without a grid', async () => {
    const html = await render({ covers: [cover('one')], name: 'Road Trip' })
    expect(html).toContain(`src="${cover('one')}"`)
    expect(html).not.toContain('grid-cols-2')
  })

  it('lays two covers out as a 2x1 grid', async () => {
    const html = await render({
      covers: [cover('one'), cover('two')],
      name: 'Road Trip',
    })
    expect(html).toContain('grid-cols-2')
    expect(html).toContain('grid-rows-1')
  })

  it('lays four covers out as a 2x2 grid', async () => {
    const html = await render({
      covers: [1, 2, 3, 4].map((n) => cover(n)),
      name: 'Road Trip',
    })
    expect(html).toContain('grid-cols-2')
    expect(html).toContain('grid-rows-2')
  })

  it('lays nine covers out as a 3x3 grid', async () => {
    const html = await render({
      covers: Array.from({ length: 9 }, (_, i) => cover(i)),
      name: 'Road Trip',
    })
    expect(html).toContain('grid-cols-3')
    expect(html).toContain('grid-rows-3')
  })

  it('falls back to the name initials when a collection has no cover', async () => {
    const html = await render({ covers: [], name: 'Road Trip' })
    expect(html).toContain('RT')
  })
})
