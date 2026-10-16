<template>
  <div>
    <!--
      The grid: one button per day, oldest week first. Cells fade in
      column by column (the stagger comes from `--i`, the column index)
      and lift under the cursor, so a year of listening arrives instead
      of appearing all at once. Hover is read off one delegated listener
      on the grid rather than 365 of them.
    -->
    <div
      class="overflow-x-auto pb-1"
      data-heatmap
      @mouseover="onHover"
      @mouseleave="hovered = null"
      @focusin="onHover"
      @focusout="hovered = null"
    >
      <div class="flex min-w-max gap-1">
        <div
          v-for="(week, w) in columns"
          :key="week[0]?.date || w"
          class="flex flex-col gap-[3px]"
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
            class="size-2 rounded-[2px] transition-transform duration-150 ease-out hover:z-10 hover:scale-150 focus-visible:z-10 focus-visible:scale-150 focus-visible:outline-none motion-reduce:transition-none motion-reduce:hover:scale-100"
            :class="[
              LEVEL_CLASSES[cell.level],
              cell.date === selected ? RING_CLASS : '',
            ]"
            :style="{ '--i': Math.min(w, STAGGER_LIMIT) }"
            :data-date="cell.date"
            :data-cell="cell.date"
            :data-selected="cell.date === selected ? cell.date : undefined"
            :aria-pressed="cell.date === selected"
            :aria-label="`${cell.date}: ${cell.count}`"
            @click="emit('select', cell.date)"
          />
        </div>
      </div>
    </div>

    <!--
      The hovered day. A native `title` can't be styled, so the visible
      one is our own and the cell carries `aria-label` for anything that
      reads the grid instead of looking at it.
    -->
    <Transition name="tip">
      <div
        v-if="hovered"
        class="pointer-events-none mt-3 inline-flex items-baseline gap-2 rounded-panel bg-surface-2 px-2.5 py-1.5 text-xs shadow-panel"
        data-heatmap-tip
      >
        <span class="font-medium">{{ formatDay(hovered.date) }}</span>
        <span class="text-faint">{{ playCount(hovered.count) }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

import {
  HEATMAP_WEEKS,
  heatmapCells,
  heatmapColumns,
  heatmapLead,
} from '/src/lib/heatmap'

const props = defineProps({
  days: { type: Array, default: () => [] },
  weeks: { type: Number, default: HEATMAP_WEEKS },
  // The day the page is showing plays for, if any: drawn with a ring so
  // the choice stays visible after the cursor moves away.
  selected: { type: String, default: '' },
  locale: { type: String, default: '' },
})

const emit = defineEmits(['select'])

// Past this many columns the stagger has already finished; clamping
// keeps the last columns from waiting longer than the first.
const STAGGER_LIMIT = 24

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

const RING_CLASS = 'ring-2 ring-accent'

const cells = computed(() => heatmapCells(props.days, props.weeks))
const columns = computed(() => heatmapColumns(cells.value))
const lead = computed(() => heatmapLead(cells.value))

// The day under the cursor (or keyboard focus), or null.
const hovered = ref(null)
const byDate = computed(
  () => new Map(cells.value.map((cell) => [cell.date, cell]))
)

/** Delegated hover: find the cell the pointer landed on. */
function onHover(event) {
  const node = event.target?.closest?.('[data-cell]')
  hovered.value = node ? (byDate.value.get(node.dataset.cell) ?? null) : null
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
  const plays = Number(count) || 0
  return plays === 1 ? '1 play' : `${plays} plays`
}
</script>

<style scoped>
/* One keyframe for every cell; each column's delay comes from `--i`. */
@keyframes heatmap-cell-in {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

button[data-cell] {
  animation: heatmap-cell-in 320ms cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
  animation-delay: calc(var(--i, 0) * 22ms);
}

@media (prefers-reduced-motion: reduce) {
  button[data-cell] {
    animation: none;
  }
}

/* The hover box fades rather than jumping under the cursor. */
.tip-enter-active,
.tip-leave-active {
  transition:
    opacity 120ms ease,
    transform 120ms ease;
}

.tip-enter-from,
.tip-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (prefers-reduced-motion: reduce) {
  .tip-enter-active,
  .tip-leave-active {
    transition: none;
  }
}
</style>
