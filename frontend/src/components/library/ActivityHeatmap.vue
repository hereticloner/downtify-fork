<template>
  <div class="overflow-x-auto pb-1">
    <div class="flex min-w-max gap-1" data-heatmap>
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
        <span
          v-for="cell in week"
          :key="cell.date"
          class="size-2 rounded-[2px]"
          :class="LEVEL_CLASSES[cell.level]"
          :data-date="cell.date"
          :title="`${cell.date}: ${cell.count}`"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import {
  HEATMAP_WEEKS,
  heatmapCells,
  heatmapColumns,
  heatmapLead,
} from '/src/lib/heatmap'

const props = defineProps({
  days: { type: Array, default: () => [] },
  weeks: { type: Number, default: HEATMAP_WEEKS },
})

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

const cells = computed(() => heatmapCells(props.days, props.weeks))
const columns = computed(() => heatmapColumns(cells.value))
const lead = computed(() => heatmapLead(cells.value))
</script>
