<template>
  <nav
    class="sticky top-11 z-20 h-10 shrink-0 items-stretch overflow-x-auto overflow-y-hidden border-b-2 border-line bg-bg [scrollbar-width:none] [&::-webkit-scrollbar]:hidden md:top-12"
    :aria-label="t('nav.main')"
  >
    <RouterLink
      v-for="item in items"
      :key="item.name"
      :to="{ name: item.name }"
      class="flex shrink-0 items-center gap-2 border-r-2 border-line px-3 transition-colors duration-100"
      :class="
        isActive(item)
          ? 'bg-invert text-on-invert'
          : 'text-muted hover:bg-surface-2 hover:text-accent'
      "
      :title="t(item.label)"
      :aria-current="isActive(item) ? 'page' : undefined"
    >
      <AppIcon :name="item.icon" :size="15" />
      <span
        class="eyebrow"
        :class="isActive(item) ? 'text-on-invert' : 'text-current'"
        >{{ t(item.label) }}</span
      >
      <span
        v-if="item.name === 'Queue' && pending"
        class="mono flex h-[18px] min-w-[18px] items-center justify-center px-1"
        :class="countClass(isActive(item))"
        :title="queuePaused ? t('queue.pausedTitle') : undefined"
        >{{ pending }}</span
      >
    </RouterLink>

    <div class="ml-auto hidden shrink-0 items-center gap-3 px-3 xl:flex">
      <a
        v-if="update?.update_available"
        :href="update.release_url"
        target="_blank"
        rel="noopener"
        class="eyebrow flex h-[24px] items-center gap-1.5 bg-invert px-2 text-on-invert"
        :title="t('nav.updateAvailable', { version: update.latest_version })"
      >
        <AppIcon name="sparkle" :size="12" />
        {{ t('nav.updateAvailable', { version: update.latest_version }) }}
      </a>
      <span v-if="version" class="mono text-faint">Downtify {{ version }}</span>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'
import { useQueuePause } from '/src/model/queuePause'
import { useUpdateCheck } from '/src/model/updateCheck'
import { usePendingCount } from './navState'

const { t } = useI18n()
const route = useRoute()
const pending = usePendingCount()
const queuePaused = useQueuePause().paused
const update = useUpdateCheck().status
const version = computed(() => {
  const v = localStorage.getItem('version')
  return v && v !== '0.0.0' ? v : ''
})

const items = [
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
  { name: 'Collections', icon: 'list', label: 'collections.title' },
  { name: 'Stats', icon: 'gauge', label: 'stats.title' },
  { name: 'Queue', icon: 'download', label: 'nav.queue' },
  {
    name: 'Discover',
    icon: 'sparkle',
    label: 'nav.discover',
    match: ['FinderBrowse'],
  },
  { name: 'Monitor', icon: 'radar', label: 'nav.monitor' },
  { name: 'Charts', icon: 'trending', label: 'nav.charts' },
  { name: 'Settings', icon: 'settings', label: 'nav.settings' },
]

function isActive(item) {
  return route.name === item.name || (item.match || []).includes(route.name)
}

// The queue count reads as a block against the tab it sits in: ink on the
// plain strip, paper on the inverted active one.
function countClass(active) {
  if (queuePaused.value) return 'border border-line-3 text-muted'
  return active ? 'bg-bg text-fg' : 'bg-invert text-on-invert'
}
</script>
