import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse, compileScript } from '@vue/compiler-sfc'

// The Stats page swaps a skeleton for its panels with a client-side
// <Transition mode="out-in">. Its else branch is a <template> holding several
// <section> roots. Vue's client compiler rejects that shape: the Transition
// raw children are flattened to multiple nodes, and at runtime out-in renders
// an empty placeholder while leaving — a blank page even though the API data
// loaded. Vitest's SSR transform treats Transition as a no-op, which is why
// the existing SSR component tests never caught it. Compiling the SFC in
// CLIENT mode reproduces the failure without a jsdom dependency.
const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '..', 'views', 'StatsView.vue'),
  'utf8'
)

describe('StatsView client render', () => {
  it('compiles in client mode instead of blanking the loaded stats', () => {
    const { descriptor } = parse(source)
    expect(() =>
      compileScript(descriptor, {
        id: 'stats-view-client',
        inlineTemplate: true,
      })
    ).not.toThrow()
  })
})
