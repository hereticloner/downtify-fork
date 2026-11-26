<template>
  <div class="grid xl:grid-cols-2">
    <div
      v-for="chart in charts"
      :key="chart.kind"
      class="border-b-2 border-line px-3 py-4 last:border-b-0 xl:border-r-2 xl:last:border-r-0"
    >
      <h3 class="eyebrow mb-3">{{ chart.title }}</h3>
      <div
        class="overflow-x-auto"
        @mouseover="onHover"
        @mouseleave="hoveredKey = ''"
        @focusin="onHover"
        @focusout="onFocusout"
      >
        <div
          class="flex h-28 min-w-max items-end gap-1"
          role="group"
          :aria-label="chart.title"
          :data-pattern-chart="chart.kind"
        >
          <button
            v-for="(row, index) in chart.rows"
            :key="row.bucket"
            type="button"
            class="pattern-cell focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-accent relative flex h-full min-w-2 flex-1 items-end"
            :data-pattern-cell="`${chart.kind}:${row.bucket}`"
            :data-pattern-kind="chart.kind"
            :data-pattern-bucket="row.bucket"
            :tabindex="tabindexFor(chart.kind, index)"
            :aria-pressed="isSelected(chart.kind, row.bucket)"
            :aria-label="`${row.full}: ${playCount(row.count)} · ${shareLabel(row.count)}`"
            :aria-describedby="
              hoveredKey === `${chart.kind}:${row.bucket}`
                ? 'pattern-tip'
                : undefined
            "
            @click="emit('select', { kind: chart.kind, bucket: row.bucket })"
            @keydown="onKeydown($event, chart, index)"
          >
            <span
              class="block w-full transition-[height] duration-100"
              :class="
                row.count
                  ? isSelected(chart.kind, row.bucket)
                    ? 'bg-fg outline-2 outline-accent'
                    : 'bg-fg'
                  : 'border border-line-2'
              "
              :style="{ height: `${row.height}%` }"
            />
          </button>
        </div>
      </div>
      <div class="mono mt-2 flex justify-between text-[9px] text-faint">
        <span>{{ chart.rows[0]?.label }}</span>
        <span>{{ chart.rows.at(-1)?.label }}</span>
      </div>
    </div>

    <Transition name="pattern-tip">
      <div
        v-if="hovered"
        id="pattern-tip"
        role="tooltip"
        class="pointer-events-none mt-2 inline-flex items-baseline gap-2 border-2 border-line bg-surface-2 px-2 py-1 xl:col-span-2"
      >
        <span class="mono text-fg">{{ hovered.row.full }}</span>
        <span class="mono text-faint">{{ playCount(hovered.row.count) }}</span>
        <span class="mono text-faint">{{ shareLabel(hovered.row.count) }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import { useI18n } from '/src/i18n'
import { patternPercent, resolvePatternKey } from '/src/lib/pattern'

const props = defineProps({
  hours: { type: Array, default: () => [] },
  weekdays: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  periodTotal: { type: Number, default: 0 },
  locale: { type: String, default: '' },
})
const emit = defineEmits(['select'])
const { t } = useI18n()

const active = ref({ hour: 0, weekday: 0 })
watch(
  () => props.selected,
  (selected) => {
    if (selected?.kind === 'hour') active.value.hour = selected.bucket
    if (selected?.kind === 'weekday') active.value.weekday = selected.bucket
  },
  { immediate: true }
)

function weekdayLabel(index, style) {
  try {
    return new Intl.DateTimeFormat(props.locale || undefined, {
      weekday: style,
      timeZone: 'UTC',
    }).format(new Date(Date.UTC(2024, 0, 7 + index)))
  } catch {
    return String(index)
  }
}

const charts = computed(() => {
  const hours = Array.isArray(props.hours) ? props.hours : []
  const weekdays = Array.isArray(props.weekdays) ? props.weekdays : []
  const hourMax = Math.max(1, ...hours.map((value) => Number(value) || 0))
  const weekdayMax = Math.max(1, ...weekdays.map((value) => Number(value) || 0))
  return [
    {
      kind: 'hour',
      title: t('stats.hourOfDayUtc'),
      rows: Array.from({ length: 24 }, (_, bucket) => {
        const count = Number(hours[bucket]) || 0
        return {
          bucket,
          count,
          label: String(bucket).padStart(2, '0'),
          full: `${String(bucket).padStart(2, '0')}:00`,
          height: (count / hourMax) * 100,
        }
      }),
    },
    {
      kind: 'weekday',
      title: t('stats.weekdayUtc'),
      rows: Array.from({ length: 7 }, (_, bucket) => {
        const count = Number(weekdays[bucket]) || 0
        return {
          bucket,
          count,
          label: weekdayLabel(bucket, 'short'),
          full: weekdayLabel(bucket, 'long'),
          height: (count / weekdayMax) * 100,
        }
      }),
    },
  ]
})

const hoveredKey = ref('')
const hovered = computed(() => {
  const [kind, rawBucket] = hoveredKey.value.split(':')
  const chart = charts.value.find((item) => item.kind === kind)
  const row = chart?.rows.find((item) => item.bucket === Number(rawBucket))
  return chart && row ? { chart, row } : null
})

function onHover(event) {
  const node = event.target?.closest?.('[data-pattern-cell]')
  if (!node) return
  hoveredKey.value = node.dataset.patternCell
  const kind = node.dataset.patternKind
  const bucket = Number(node.dataset.patternBucket)
  if (kind === 'hour' || kind === 'weekday') active.value[kind] = bucket
}

function onFocusout(event) {
  if (event.relatedTarget?.closest?.('[data-pattern-cell]')) return
  hoveredKey.value = ''
}

function tabindexFor(kind, index) {
  return index === active.value[kind] ? 0 : -1
}

function isSelected(kind, bucket) {
  return props.selected?.kind === kind && props.selected?.bucket === bucket
}

function onKeydown(event, chart, index) {
  const intent = resolvePatternKey(event, index, chart.rows.length)
  if (!intent) return
  event.preventDefault?.()
  event.stopPropagation?.()
  active.value[chart.kind] = intent.index
  if (intent.type === 'activate') {
    emit('select', { kind: chart.kind, bucket: intent.index })
    return
  }
  const nodes = event.currentTarget
    .closest('[data-pattern-chart]')
    .querySelectorAll('[data-pattern-cell]')
  nodes[intent.index]?.focus?.()
}

function playCount(count) {
  return t('stats.playCount', { count: Number(count) || 0 })
}

function shareLabel(count) {
  return t('stats.patternShare', {
    percent: Math.round(patternPercent(count, props.periodTotal)),
  })
}
</script>

<style scoped>
@media (pointer: coarse) {
  .pattern-cell {
    min-width: 24px;
  }
}

.pattern-tip-enter-active,
.pattern-tip-leave-active {
  transition: opacity 100ms linear;
}

.pattern-tip-enter-from,
.pattern-tip-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .pattern-tip-enter-active,
  .pattern-tip-leave-active {
    transition: none;
  }
}
</style>
