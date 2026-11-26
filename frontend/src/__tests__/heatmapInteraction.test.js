import { afterEach, describe, expect, it, vi } from 'vitest'
import { computed, reactive, ref } from 'vue'
import { readFileSync } from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'

import { setLocale, t } from '/src/i18n'
import {
  HEATMAP_WEEKS,
  heatmapCells,
  heatmapColumns,
  heatmapLead,
  resolveHeatmapKey,
} from '/src/lib/heatmap'

const source = readFileSync(
  new URL('../components/library/ActivityHeatmap.vue', import.meta.url),
  'utf8'
)
const { descriptor } = parse(source)
const { content } = compileScript(descriptor, {
  id: 'heatmap-interaction',
  inlineTemplate: false,
})
const kept = []
let skipping = false
for (const line of content.split('\n')) {
  if (skipping) {
    if (line.includes('from ')) skipping = false
    continue
  }
  if (line.startsWith('import ')) {
    if (!line.includes('from ')) skipping = true
    continue
  }
  kept.push(line)
}
const factory = new Function(
  'computed',
  'ref',
  'useI18n',
  'HEATMAP_WEEKS',
  'heatmapCells',
  'heatmapColumns',
  'heatmapLead',
  'resolveHeatmapKey',
  kept.join('\n').replace('export default', 'return')
)
const component = factory(
  computed,
  ref,
  () => ({ t }),
  HEATMAP_WEEKS,
  heatmapCells,
  heatmapColumns,
  heatmapLead,
  resolveHeatmapKey
)

function setup(days, extra = {}) {
  const props = reactive({
    days,
    weeks: HEATMAP_WEEKS,
    selected: '',
    locale: 'en',
    ...extra,
  })
  const emitted = []
  const bindings = component.setup(props, {
    emit: (...args) => emitted.push(args),
    expose() {},
  })
  return { props, bindings, emitted }
}

const cellEvent = (date) => ({
  target: {
    closest: (selector) =>
      selector === '[data-cell]' ? { dataset: { cell: date } } : null,
  },
})
const gapEvent = () => ({ target: { closest: () => null } })

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ActivityHeatmap interaction', () => {
  it('keeps the tooltip over internal grid gaps', () => {
    const { bindings } = setup([
      { date: '2026-11-20', count: 7 },
      { date: '2026-11-21', count: 2 },
    ])
    bindings.onHover(cellEvent('2026-11-20'))
    expect(bindings.hovered.value?.count).toBe(7)

    bindings.onHover(gapEvent())

    expect(bindings.hovered.value?.count).toBe(7)
  })

  it('follows refreshed data for the hovered date', () => {
    const { props, bindings } = setup([
      { date: '2026-11-20', count: 7 },
      { date: '2026-11-21', count: 2 },
    ])
    bindings.onHover(cellEvent('2026-11-20'))
    props.days = [
      { date: '2026-11-20', count: 99 },
      { date: '2026-11-21', count: 2 },
    ]

    expect(bindings.hovered.value?.count).toBe(99)
  })

  it('does not clear focus tooltips when focus stays inside the grid', () => {
    const { bindings } = setup([{ date: '2026-11-20', count: 7 }])
    bindings.onHover(cellEvent('2026-11-20'))
    bindings.onFocusout({
      relatedTarget: { closest: () => ({ dataset: { cell: '2026-11-21' } }) },
    })
    expect(bindings.hovered.value?.count).toBe(7)

    bindings.onFocusout({ relatedTarget: { closest: () => null } })
    expect(bindings.hovered.value).toBeNull()
  })

  it('moves the single tab stop with two-dimensional keys', () => {
    const focus = vi.fn()
    vi.stubGlobal('document', {
      querySelectorAll: () => Array.from({ length: 28 }, () => ({ focus })),
    })
    const { bindings } = setup(
      Array.from({ length: 28 }, (_, index) => ({
        date: `2026-11-${String(index + 1).padStart(2, '0')}`,
        count: 1,
      }))
    )
    const event = {
      key: 'ArrowDown',
      currentTarget: {},
      target: {},
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
    }

    bindings.onCellKeydown(event, 0)

    expect(bindings.activeIndex.value).toBe(7)
    expect(focus).toHaveBeenCalledTimes(1)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(event.stopPropagation).toHaveBeenCalled()
  })

  it('uses localized play text and tooltip semantics', async () => {
    await setLocale('tr')
    const { bindings } = setup([], { locale: 'tr' })
    expect(bindings.playCount(2)).toBe('2 çalma')
    expect(descriptor.template.content).toContain('role="tooltip"')
    expect(descriptor.template.content).toContain('aria-describedby')
    await setLocale('en')
  })
})
