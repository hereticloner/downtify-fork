<template>
  <div
    role="row"
    class="flex h-10 items-center gap-3 border-b-2 border-line bg-surface-2 px-3 max-sm:hidden"
  >
    <span v-if="selectable" class="size-4 shrink-0" aria-hidden="true" />
    <span role="columnheader" class="eyebrow w-6 text-center">#</span>
    <span class="size-10 shrink-0" aria-hidden="true" />
    <span role="columnheader" class="eyebrow min-w-0 flex-1 text-fg">{{
      t('track.title')
    }}</span>
    <span
      v-if="!hideAlbum"
      role="columnheader"
      class="eyebrow w-[26%] max-lg:hidden"
      >{{ t('track.album') }}</span
    >
    <span role="columnheader" class="w-12 text-right">
      <AppIcon name="clock" :size="13" class="inline" />
    </span>
    <span :class="[actionsWidth, 'shrink-0']" aria-hidden="true" />
  </div>
</template>

<script setup>
// The column headings for a list of TrackDownPlay rows, in the style of
// TrackList's. Its columns are the row's, so the two have to change together
// (widths, and what is hidden at which breakpoint).
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'

defineProps({
  // Matches a leading spacer to TrackDownPlay's own checkbox column, so
  // the rest of the columns stay aligned when its rows are selectable.
  selectable: { type: Boolean, default: false },
  // Matches TrackDownPlay's own `hideAlbum`.
  hideAlbum: { type: Boolean, default: false },
  // Matches the rows' action column width (TrackDownPlay keeps `w-28`;
  // the Similar rows carry the wand extra, so they ask for `w-40`).
  actionsWidth: { type: String, default: 'w-28' },
})

const { t } = useI18n()
</script>
