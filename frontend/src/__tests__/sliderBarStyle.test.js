// SliderBar accepts optional inline overrides for its fill/thumb so a
// caller (MiniPlayer) can tint progress with the cover palette while the
// classes stay as the fallback. Rendered with SSR like moreSheetA11y.
import { beforeAll, describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

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
  activeElement: null,
  documentElement: { setAttribute: () => {}, style: {} },
  createElement: () => ({ style: {} }),
  querySelector: () => null,
  addEventListener: () => {},
  removeEventListener: () => {},
}

let SliderBar

beforeAll(async () => {
  ;({ default: SliderBar } =
    await import('/src/components/player/SliderBar.vue'))
})

async function render(props) {
  const app = createSSRApp({ render: () => h(SliderBar, props) })
  return renderToString(app)
}

describe('SliderBar palette overrides', () => {
  it('leaves fill/thumb to classes by default', async () => {
    const html = await render({ modelValue: 30, max: 100 })
    expect(html).toContain('bg-fg')
    expect(html).not.toContain('background-color')
  })

  it('paints fill and thumb from the given styles', async () => {
    const html = await render({
      modelValue: 30,
      max: 100,
      fillStyle: { backgroundColor: '#1a8033' },
      thumbStyle: { backgroundColor: '#1a8033' },
    })
    expect(html.match(/#1a8033/g)?.length).toBe(2)
  })
})
