import { beforeAll, describe, expect, it, vi } from 'vitest'

// The sheet reaches auth (via the API model) and the update check; stub
// both so no request, socket or interval is touched.
vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    onForbidden: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({
        data: { signed_in: true, user: { role: 'admin', username: 'me' } },
      }),
  },
}))
vi.mock('/src/model/updateCheck', () => ({
  useUpdateCheck: () => ({ status: { value: null } }),
}))

// The sheet's dialog reaches player/i18n/theme models, which read a few
// browser globals at import time. A minimal shim keeps the SSR render in
// Node — same approach as selection.test.js (no jsdom dependency).
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

import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

const LINKS = [
  { name: 'Monitor', icon: 'radar', label: 'nav.monitor' },
  { name: 'Settings', icon: 'settings', label: 'nav.settings' },
]

// Dialog content lives in a <Teleport to="body">, so SSR puts it in
// `ctx.teleports` rather than the page string; join both for assertions.
async function render(component, props) {
  const app = createSSRApp({ render: () => h(component, props) })
  app.component('RouterLink', {
    props: { to: { type: [String, Object], default: null } },
    setup(_, { slots }) {
      return () => h('a', {}, slots.default ? slots.default() : [])
    },
  })
  const ctx = {}
  const html = await renderToString(app, ctx)
  return html + Object.values(ctx.teleports || {}).join('')
}

describe('MoreSheet', () => {
  let MoreSheet

  beforeAll(async () => {
    MoreSheet = (await import('/src/components/shell/MoreSheet.vue')).default
  })

  it('renders as a labelled, modal dialog', async () => {
    const html = await render(MoreSheet, { open: true, links: LINKS })
    expect(html).toContain('role="dialog"')
    expect(html).toContain('aria-modal="true"')
    expect(html).toMatch(/aria-labelledby="modal-[^"]+"/)
    // The heading the dialog is labelled by, and every destination.
    expect(html).toMatch(/<h2[^>]*>More<\/h2>/)
    expect(html).toContain('Monitor')
    expect(html).toContain('Settings')
  })

  it('offers a close control with an accessible name', async () => {
    const html = await render(MoreSheet, { open: true, links: LINKS })
    expect(html).toMatch(/aria-label="Close"/)
  })

  it('renders no dialog while closed', async () => {
    const html = await render(MoreSheet, { open: false, links: LINKS })
    expect(html).not.toContain('role="dialog"')
    expect(html).not.toContain('aria-modal')
  })
})
