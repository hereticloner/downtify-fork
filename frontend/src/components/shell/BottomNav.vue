<template>
  <MoreSheet :open="open" :links="links" @close="$emit('close')" />
</template>

<script setup>
// Phones have no tab bar: the ☰ block in the header opens this full-height
// menu, which carries every destination the desktop strip shows plus the
// theme and sign-out blocks.
import { computed, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useRoute } from 'vue-router'
import MoreSheet from './MoreSheet.vue'
import { useQueuePause } from '/src/model/queuePause'
import { usePendingCount } from './navState'

defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close'])

const route = useRoute()
const pending = usePendingCount()
const queuePaused = useQueuePause().paused

const destinations = [
  { name: 'Home', icon: 'home', label: 'nav.home' },
  {
    name: 'Search',
    icon: 'search',
    label: 'nav.search',
    match: ['Link', 'TopSongs'],
  },
  {
    name: 'Library',
    icon: 'library',
    label: 'nav.library',
    match: ['Album', 'Artist', 'Playlist', 'LibraryHealth', 'LyricsHealth'],
  },
  { name: 'Queue', icon: 'download', label: 'nav.queue' },
  {
    name: 'Discover',
    icon: 'sparkle',
    label: 'nav.discover',
    match: ['FinderBrowse'],
  },
  { name: 'Monitor', icon: 'radar', label: 'nav.monitor' },
  { name: 'Charts', icon: 'trending', label: 'nav.charts' },
  { name: 'Collections', icon: 'list', label: 'collections.title' },
  { name: 'Stats', icon: 'gauge', label: 'stats.title' },
  { name: 'Settings', icon: 'settings', label: 'nav.settings' },
]

const links = computed(() =>
  destinations.map((item) => ({
    ...item,
    active: route.name === item.name || (item.match || []).includes(route.name),
    count:
      item.name === 'Queue' && pending.value && !queuePaused.value
        ? pending.value
        : 0,
  }))
)

// Following a link closes the panel; the route watch also covers links
// opened from elsewhere while the menu was up.
watch(
  () => route.fullPath,
  () => emit('close')
)

// Growing past the phone layout reveals the desktop strip; a menu left
// open would sit on top of it.
const isDesktop = useMediaQuery('(min-width: 768px)')
watch(isDesktop, (desktop) => {
  if (desktop) emit('close')
})
</script>
