<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-side/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl"
    :aria-label="t('nav.main')"
  >
    <div class="flex h-[4.75rem] items-stretch px-1 pt-1.5">
      <RouterLink
        v-for="item in items"
        :key="item.name"
        :to="{ name: item.name }"
        class="relative flex flex-1 flex-col items-center gap-1 pt-1.5"
        :class="isActive(item) ? 'text-fg' : 'text-faint'"
      >
        <AppIcon
          :name="item.icon"
          :size="22"
          :class="isActive(item) ? 'text-accent' : ''"
        />
        <span
          class="text-[10px]"
          :class="isActive(item) ? 'font-semibold' : 'font-medium'"
        >
          {{ t(item.label) }}
        </span>
        <span
          v-if="item.name === 'Queue' && pending"
          class="tabular absolute top-0 left-[calc(50%+4px)] flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-bold text-on-accent"
          >{{ pending }}</span
        >
      </RouterLink>
      <button
        type="button"
        class="relative flex flex-1 flex-col items-center gap-1 pt-1.5"
        :class="moreActive ? 'text-fg' : 'text-faint'"
        @click="sheet = true"
      >
        <AppIcon
          name="more"
          :size="22"
          :class="moreActive ? 'text-accent' : ''"
        />
        <span
          class="text-[10px]"
          :class="moreActive ? 'font-semibold' : 'font-medium'"
        >
          {{ t('nav.more') }}
        </span>
        <span
          v-if="hasUpdate"
          class="absolute top-1 left-[calc(50%+6px)] size-2 rounded-full bg-accent"
        />
      </button>
    </div>

    <MoreSheet :open="sheet" :links="moreLinks" @close="sheet = false" />
  </nav>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import MoreSheet from './MoreSheet.vue'
import { useI18n } from '/src/i18n'
import { useUpdateCheck } from '/src/model/updateCheck'
import { usePendingCount } from './navState'

const { t } = useI18n()
const route = useRoute()
const pending = usePendingCount()
const sheet = ref(false)
const update = useUpdateCheck().status
const hasUpdate = computed(() => Boolean(update.value?.update_available))

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
    match: ['Album', 'Artist', 'Playlist'],
  },
  { name: 'Queue', icon: 'download', label: 'nav.queue' },
]
const moreLinks = [
  {
    name: 'Discover',
    icon: 'sparkle',
    label: 'nav.discover',
    match: ['FinderBrowse'],
  },
  { name: 'Monitor', icon: 'radar', label: 'nav.monitor' },
  { name: 'Podcasts', icon: 'mic', label: 'nav.podcasts' },
  { name: 'Charts', icon: 'trending', label: 'nav.charts' },
  { name: 'Collections', icon: 'list', label: 'collections.title' },
  { name: 'Stats', icon: 'gauge', label: 'stats.title' },
  { name: 'Settings', icon: 'settings', label: 'nav.settings' },
]

function isActive(item) {
  return route.name === item.name || (item.match || []).includes(route.name)
}

const moreActive = computed(() => moreLinks.some(isActive))

watch(
  () => route.fullPath,
  () => (sheet.value = false)
)
</script>
