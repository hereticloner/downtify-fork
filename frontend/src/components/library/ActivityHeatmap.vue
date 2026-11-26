<template>
  <div>
    <!--
      The grid: one painted 2px block per day, oldest week first. Pointer
      targets stay compact on fine pointers and grow on touch screens.
    -->
    <div
      class="overflow-x-auto pb-1"
      data-heatmap
      role="group"
      :aria-label="t('stats.activityHeatmap')"
      aria-describedby="heatmap-help"
      @mouseover="onHover"
      @mouseleave="hoveredDate = ''"
      @focusin="onHover"
      @focusout="onFocusout"
    >
      <span id="heatmap-help" class="sr-only">{{
        t('stats.heatmapKeyboardHint')
      }}</span>
      <div class="stagger flex min-w-max gap-0.5">
        <div
          v-for="(week, w) in columns"
          :key="week[0]?.date || w"
          class="flex flex-col gap-0.5"
        >
          <span
            v-for="n in w === 0 ? lead : 0"
            :key="`lead-${n}`"
            class="size-2"
            aria-hidden="true"
          />
          <button
            v-for="cell in week"
            :key="cell.date"
            type="button"
            class="heatmap-cell focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-accent"
            :data-date="cell.date"
            :data-cell="cell.date"
            :data-selected="cell.date === selected ? cell.date : undefined"
            :tabindex="tabindexFor(indexByDate.get(cell.date))"
            :aria-pressed="cell.date === selected"
            :aria-label="`${formatDay(cell.date)}: ${playCount(cell.count)}`"
            :aria-describedby="
              cell.date === hoveredDate ? 'heatmap-tip' : undefined
            "
            @click="emit('select', cell.date)"
            @keydown="onCellKeydown($event, indexByDate.get(cell.date))"
          >
            <span
              class="size-2 transition-colors duration-100"
              :class="[
                LEVEL_CLASSES[cell.level],
                cell.date === selected ? SELECTED_CLASS : '',
              ]"
            />
          </button>
        </div>
      </div>
    </div>

    <!-- The hovered or focused day, derived from its date so refreshes follow. -->
    <Transition name="tip">
      <div
        v-if="hovered"
        id="heatmap-tip"
        role="tooltip"
        class="pointer-events-none mt-2 inline-flex items-baseline gap-2 border-2 border-line bg-surface-2 px-2 py-1"
        data-heatmap-tip
      >
        <span class="mono text-fg">{{ formatDay(hovered.date) }}</span>
        <span class="mono text-faint">{{ playCount(hovered.count) }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

import { useI18n } from '/src/i18n'
import {
  HEATMAP_WEEKS,
  heatmapCells,
  heatmapColumns,
  heatmapLead,
  resolveHeatmapKey,
} from '/src/lib/heatmap'

const props = defineProps({
  days: { type: Array, default: () => [] },
  weeks: { type: Number, default: HEATMAP_WEEKS },
  // The day the page is showing plays for, if any: drawn with an accent
  // frame so the choice stays visible after the cursor moves away.
  selected: { type: String, default: '' },
  locale: { type: String, default: '' },
})

const emit = defineEmits(['select'])
const { t } = useI18n()

// Written out rather than interpolated (`bg-accent/${level * 25}`) so
// Tailwind sees each class as a whole. Level 0 is the empty-cell grey,
// the rest step up in opacity.
const LEVEL_CLASSES = [
  'bg-line-2',
  'bg-accent/25',
  'bg-accent/50',
  'bg-accent/75',
  'bg-accent',
]

// The picked day keeps an accent frame. Hover never replaces it.
const SELECTED_CLASS = 'outline-2 outline-accent'

const cells = computed(() => heatmapCells(props.days, props.weeks))
const columns = computed(() => heatmapColumns(cells.value))
const lead = computed(() => heatmapLead(cells.value))
const byDate = computed(
  () => new Map(cells.value.map((cell) => [cell.date, cell]))
)
const indexByDate = computed(
  () => new Map(cells.value.map((cell, index) => [cell.date, index]))
)

// Store the date, not a cell snapshot: refreshed counts follow the pointer.
const hoveredDate = ref('')
const hovered = computed(() =>
  hoveredDate.value ? (byDate.value.get(hoveredDate.value) ?? null) : null
)
const activeIndex = ref(0)

/** Delegated hover/focus: gaps inside the grid are not an exit. */
function onHover(event) {
  const node = event.target?.closest?.('[data-cell]')
  if (!node) return
  const date = node.dataset.cell
  if (!byDate.value.has(date)) return
  hoveredDate.value = date
  activeIndex.value = indexByDate.value.get(date) ?? activeIndex.value
}

function onFocusout(event) {
  if (event.relatedTarget?.closest?.('[data-cell]')) return
  hoveredDate.value = ''
}

function tabindexFor(index) {
  return index === activeIndex.value ? 0 : -1
}

function onCellKeydown(event, index) {
  const intent = resolveHeatmapKey(event, index, cells.value.length)
  if (!intent) return
  event.preventDefault?.()
  event.stopPropagation?.()
  activeIndex.value = intent.index
  if (intent.type === 'activate') {
    const cell = cells.value[intent.index]
    if (cell) emit('select', cell.date)
    return
  }
  const nodes = document.querySelectorAll('[data-heatmap] [data-cell]')
  nodes[intent.index]?.focus?.()
}

/**
 * The day in the reader's own language. The date arrives as a plain
 * `YYYY-MM-DD` and is parsed as UTC, so a timezone east of Greenwich
 * can't slide it onto the previous day.
 */
function formatDay(date) {
  const parsed = Date.parse(`${String(date || '')}T00:00:00Z`)
  if (Number.isNaN(parsed)) return String(date || '')
  try {
    return new Intl.DateTimeFormat(props.locale || undefined, {
      dateStyle: 'full',
      timeZone: 'UTC',
    }).format(new Date(parsed))
  } catch {
    return String(date || '')
  }
}

function playCount(count) {
  return t('stats.playCount', { count: Number(count) || 0 })
}
</script>

<style scoped>
.heatmap-cell {
  display: grid;
  width: 8px;
  height: 8px;
  place-items: center;
}

@media (pointer: coarse) {
  .heatmap-cell {
    width: 24px;
    height: 24px;
  }
}

/* The hover box fades rather than jumping under the cursor. */
.tip-enter-active,
.tip-leave-active {
  transition: opacity 100ms linear;
}

.tip-enter-from,
.tip-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .tip-enter-active,
  .tip-leave-active {
    transition: none;
  }
}
</style>
