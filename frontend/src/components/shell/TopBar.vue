<template>
  <header class="sticky top-0 z-30 border-b-2 border-line bg-bg">
    <div class="flex h-11 items-stretch md:h-12">
      <!-- Phones: the whole menu lives behind this block. -->
      <button
        type="button"
        class="flex w-11 shrink-0 items-center justify-center border-r-2 border-line text-fg transition-colors duration-100 hover:bg-surface-2 md:hidden"
        :aria-label="t('nav.more')"
        aria-haspopup="dialog"
        @click="$emit('menu')"
      >
        <AppIcon name="menu" :size="20" />
      </button>

      <RouterLink
        :to="{ name: 'Home' }"
        class="flex shrink-0 items-center gap-2 border-r-2 border-line px-2.5 md:px-4"
        :title="t('nav.home')"
      >
        <AppLogo :size="22" />
        <span
          class="text-display text-[15px] font-bold tracking-[0.06em] uppercase"
          >Downtify</span
        >
      </RouterLink>

      <!-- One search box, shared by both layouts: it sits in the masthead
           row on desktop and drops below it on a phone. -->
      <div
        class="min-w-0 md:flex md:flex-1 md:items-center md:px-2"
        :class="
          searchOpen
            ? 'max-md:absolute max-md:inset-x-0 max-md:top-full max-md:z-10 max-md:border-t-2 max-md:border-b-2 max-md:border-line max-md:bg-bg max-md:p-1'
            : 'max-md:hidden'
        "
      >
        <GlobalSearch class="w-full" />
      </div>

      <div class="ml-auto flex shrink-0 items-stretch md:ml-0">
        <div class="hidden items-center gap-1 px-2 lg:flex">
          <UiIconButton
            icon="chevron-left"
            :label="t('nav.back')"
            size="sm"
            :disabled="!canGoBack"
            @click="router.back()"
          />
          <UiIconButton
            icon="chevron-right"
            :label="t('nav.forward')"
            size="sm"
            :disabled="!canGoForward"
            @click="router.forward()"
          />
        </div>
        <div class="hidden items-center gap-1 px-2 xl:flex">
          <UiIconButton
            icon="keyboard"
            :label="t('shortcuts.title')"
            size="sm"
            @click="openShortcuts"
          />
        </div>
        <div class="hidden items-center gap-1 px-2 sm:flex">
          <UiIconButton
            :icon="theme.resolved.value === 'dark' ? 'sun' : 'moon'"
            :label="
              theme.resolved.value === 'dark'
                ? t('settings.themeLight')
                : t('settings.themeDark')
            "
            size="sm"
            @click="theme.toggle()"
          />
        </div>

        <button
          type="button"
          class="flex w-11 shrink-0 items-center justify-center border-l-2 border-line text-fg transition-colors duration-100 hover:bg-surface-2 md:hidden"
          :class="searchOpen ? 'bg-invert text-on-invert' : ''"
          :aria-label="t('nav.search')"
          :aria-expanded="searchOpen"
          @click="toggleSearch"
        >
          <AppIcon name="search" :size="19" />
        </button>

        <RouterLink
          :to="{ name: 'Queue' }"
          class="hidden shrink-0 items-center gap-2 border-l-2 border-line px-3 transition-colors duration-100 md:flex"
          :class="
            route.name === 'Queue'
              ? 'bg-invert text-on-invert hover:bg-invert'
              : 'text-fg hover:bg-surface-2'
          "
          :title="queuePaused ? t('queue.pausedTitle') : t('nav.queue')"
          :aria-label="t('nav.queue')"
          :aria-current="route.name === 'Queue' ? 'page' : undefined"
        >
          <AppIcon name="download" :size="17" />
          <span class="eyebrow hidden text-current lg:inline">{{
            t('nav.queue')
          }}</span>
          <span
            v-if="pending"
            class="mono flex h-[18px] min-w-[18px] items-center justify-center px-1"
            :class="countClass"
            >{{ pending }}</span
          >
        </RouterLink>

        <div
          v-if="auth.user.value"
          class="hidden shrink-0 items-stretch border-l-2 border-line md:flex"
        >
          <span
            class="mono hidden max-w-[16ch] items-center truncate px-3 text-muted xl:flex"
            >{{ auth.user.value.username }}</span
          >
          <UiIconButton
            v-if="!auth.authDisabled.value"
            icon="log-out"
            :label="t('nav.signOutAs', { name: auth.user.value.username })"
            size="sm"
            class="m-1.5"
            @click="auth.signOut"
          />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import AppLogo from '../ui/AppLogo.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import GlobalSearch from './GlobalSearch.vue'
import { useAuth } from '/src/model/auth'
import { useQueuePause } from '/src/model/queuePause'
import { useTheme } from '/src/model/theme'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'
import { usePendingCount } from './navState'

defineEmits(['menu'])

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const theme = useTheme()
const auth = useAuth()
const ui = useUi()
const pending = usePendingCount()
const queuePaused = useQueuePause().paused
const searchOpen = ref(false)

// vue-router records where history can go in history.state.
const canGoBack = computed(() => {
  route.fullPath
  return !!window.history.state?.back
})
const canGoForward = computed(() => {
  route.fullPath
  return !!window.history.state?.forward
})

// The queue count is a block in the ink colour, unless this is the page
// we are already on (then it has to read against the inverted tab).
const countClass = computed(() => {
  if (queuePaused.value) return 'border border-line-3 text-muted'
  return route.name === 'Queue' ? 'bg-bg text-fg' : 'bg-invert text-on-invert'
})

async function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (!searchOpen.value) return
  // The box is only in the layout once the row is open.
  await nextTick()
  ui.focusSearch()
}

watch(
  () => route.fullPath,
  () => (searchOpen.value = false)
)

function openShortcuts() {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: '?' }))
}
</script>
