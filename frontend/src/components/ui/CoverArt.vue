<template>
  <div
    class="relative isolate shrink-0 overflow-hidden border-2 border-line bg-surface-2"
  >
    <div
      v-if="mosaic.length >= 2"
      class="grid size-full gap-0.5 bg-line"
      :class="gridClass"
    >
      <img
        v-for="(url, i) in mosaic.slice(0, MAX_MOSAIC)"
        :key="i"
        :src="url"
        alt=""
        loading="lazy"
        decoding="async"
        class="size-full min-h-0 min-w-0 object-cover"
        :class="i === 0 && mosaic.length === 3 ? 'row-span-2' : ''"
      />
    </div>
    <img
      v-else-if="imageSrc && !failed"
      :src="imageSrc"
      :alt="alt"
      loading="lazy"
      decoding="async"
      class="size-full object-cover transition-opacity duration-100"
      :class="ready ? 'opacity-100' : 'opacity-0'"
      @load="ready = true"
      @error="onImageError"
    />
    <div
      v-if="showFallback"
      class="absolute inset-0 flex"
      :class="
        symbol
          ? 'items-center justify-center'
          : 'items-end justify-start p-[8%]'
      "
    >
      <AppIcon
        v-if="!letters"
        :name="icon"
        :size="iconSize"
        class="text-faint"
      />
      <span v-else class="eyebrow leading-none select-none">{{ letters }}</span>
    </div>
    <slot />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { MAX_MOSAIC, mosaicGrid } from '/src/lib/mosaic'
import { initials } from '/src/lib/format'

const props = defineProps({
  src: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  alt: { type: String, default: '' },
  name: { type: String, default: '' },
  icon: { type: String, default: 'music' },
  round: { type: Boolean, default: false },
  rounded: { type: String, default: 'rounded-cover' },
  shadow: { type: Boolean, default: false },
  letterSize: { type: Number, default: 48 },
  iconSize: { type: Number, default: 28 },
  // The icon on a fixed tile, whatever art or name there is — for
  // collections that are recognised by what they are, like liked songs.
  symbol: { type: Boolean, default: false },
  // Optional second image tried once `src` fails to load, before giving up
  // on the initials: for a `src` that may simply not exist (an artist photo
  // from a proxy), with a picture known to. Unset = today's behaviour.
  fallback: { type: String, default: '' },
})

const failed = ref(false)
const ready = ref(false)
const usingFallback = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
    ready.value = false
    usingFallback.value = false
  }
)

function onImageError() {
  if (props.fallback && !usingFallback.value) {
    usingFallback.value = true
    ready.value = false
    return
  }
  failed.value = true
}

// A real cover always wins: a playlist with its own artwork shows it
// instead of a grid of the tracks it happens to contain.
const mosaic = computed(() =>
  props.symbol || props.src ? [] : props.covers.filter(Boolean)
)
// Written out (not built from a template literal) so Tailwind sees the
// classes in the source and generates them.
const COLUMN_CLASSES = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
}
const ROW_CLASSES = { 1: 'grid-rows-1', 2: 'grid-rows-2', 3: 'grid-rows-3' }
const gridClass = computed(() => {
  const { columns, rows } = mosaicGrid(mosaic.value.length)
  return `${COLUMN_CLASSES[columns]} ${ROW_CLASSES[rows]}`
})
const imageSrc = computed(() => {
  if (props.symbol) return ''
  if (usingFallback.value) return props.fallback
  return props.src || mosaic.value[0] || ''
})
const letters = computed(() => (props.symbol ? '' : initials(props.name)))
const showFallback = computed(
  () => mosaic.value.length < 2 && (!imageSrc.value || failed.value)
)
</script>
