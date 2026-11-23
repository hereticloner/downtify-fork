<template>
  <SignIn v-if="auth.mustSignIn.value" />
  <div v-else class="flex min-h-dvh flex-col bg-bg text-fg">
    <TopBar @menu="menuOpen = true" />
    <!-- B6 — 2px accent rule directly under the masthead. -->
    <Transition name="progress">
      <div
        v-if="progressActive"
        class="route-progress"
        :class="{ 'is-complete': progressComplete }"
        aria-hidden="true"
      >
        <span class="route-progress-fill" />
      </div>
    </Transition>
    <SideNav class="hidden md:flex" />
    <main class="route-view-root min-w-0 flex-1" :class="contentPad">
      <RouterView v-slot="{ Component, route: viewRoute }">
        <Transition :name="pageTransitionName" mode="out-in">
          <component :is="Component" :key="viewKey(viewRoute)" />
        </Transition>
      </RouterView>
    </main>

    <!-- Transport: MiniPlayer owns the fixed bottom bar (56px on a phone,
         64px on desktop); the content column reserves that height. -->
    <MiniPlayer v-if="hasTransport" />

    <BottomNav :open="menuOpen" @close="menuOpen = false" />
    <NowPlaying />
    <ShortcutsDialog v-model:open="shortcutsOpen" />
    <UiToasts />
    <UiDialog />
    <CreatePlaylistModal />
    <RenamePlaylistModal />
    <AddTracksToPlaylistModal />
    <DefaultPasswordPrompt />
    <ReplaceAudioDialog v-if="auth.isAdmin.value" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SideNav from './SideNav.vue'
import TopBar from './TopBar.vue'
import BottomNav from './BottomNav.vue'
import MiniPlayer from './MiniPlayer.vue'
import NowPlaying from './NowPlaying.vue'
import ShortcutsDialog from './ShortcutsDialog.vue'
import UiToasts from '../ui/UiToasts.vue'
import UiDialog from '../ui/UiDialog.vue'
import CreatePlaylistModal from '../library/CreatePlaylistModal.vue'
import RenamePlaylistModal from '../library/RenamePlaylistModal.vue'
import AddTracksToPlaylistModal from '../library/AddTracksToPlaylistModal.vue'
import SignIn from './SignIn.vue'
import DefaultPasswordPrompt from './DefaultPasswordPrompt.vue'
import ReplaceAudioDialog from '../library/ReplaceAudioDialog.vue'
import { useRouteProgress } from '/src/composables/useRouteProgress'
import {
  prefersReducedMotion,
  supportsViewTransitions,
} from '/src/lib/viewTransitions'
import API from '/src/model/api'
import { useAccount } from '/src/model/account'
import { useAuth } from '/src/model/auth'
import { useI18n } from '/src/i18n'
import { usePlayer } from '/src/model/player'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useSettingsManager } from '/src/model/settings'
import { useLibrary } from '/src/model/library'
import { useDiscover } from '/src/model/discover'
import { useNowPlaying, useUi } from '/src/model/ui'
import { startRateLimitNotifier } from '/src/model/spotifySync'
import { useShortcuts } from './shortcuts'

const auth = useAuth()
const account = useAccount()
const { t } = useI18n()
const player = usePlayer()
const { showLyrics } = usePlayerPrefs()
const settings = useSettingsManager().settings
const route = useRoute()
const router = useRouter()
const ui = useUi()
const nowPlaying = useNowPlaying()
const shortcutsOpen = ref(false)
const menuOpen = ref(false)

// The browser snapshots the swap when View Transitions are available, so the
// out-in page transition would fight it; keep it as the fallback only.
const pageTransitionName =
  supportsViewTransitions() && !prefersReducedMotion() ? '' : 'page'
const { active: progressActive, complete: progressComplete } =
  useRouteProgress()

// The transport only takes room when there is a bar to show; the content
// column reserves exactly that height so nothing ends underneath it.
const hasTransport = computed(
  () =>
    settings.mini_player_enabled !== false && Boolean(player.currentTrack.value)
)
const contentPad = computed(() =>
  hasTransport.value ? 'pb-14 md:pb-16' : 'pb-8'
)

// The Now playing overlay lives in the query string (?np=1); it must not
// remount the page underneath it.
function viewKey(viewRoute) {
  return viewRoute.meta.viewKey || viewRoute.path
}

useLibrary().load()
// The account's own preferences (theme, language...) and telling the
// server what plays here, once someone is signed in.
watch(
  () => auth.user.value?.id,
  (id) => {
    if (!id) return
    account.start()
    account.startPlaybackReports()
  },
  { immediate: true }
)
API.onForbidden(() => {
  ui.toast(t('account.needsAdmin'), { kind: 'error' })
})
// Count listens for Discover, whichever page the music is playing on.
useDiscover().startListenTracking()
// The background sync's rate limit has to be said out loud wherever the
// user is — otherwise an hour of skipped playlists is a feature that
// looks broken, and nothing on the page says otherwise.
startRateLimitNotifier()

useShortcuts({
  player,
  nowPlaying,
  // "L" opens the lyrics panel, which isn't there when they're hidden.
  lyricsEnabled: () => showLyrics.value,
  focusSearch: ui.focusSearch,
  openHelp: () => (shortcutsOpen.value = true),
  goTo: (name) => router.push({ name }),
  // A modal on top swallows every shortcut; Escape closes it.
  closeModal: () => {
    if (ui.closeTopModal()) return true
    if (ui.dialog.value) {
      ui.closeDialog(false)
      return true
    }
    if (shortcutsOpen.value) {
      shortcutsOpen.value = false
      return true
    }
    return false
  },
  hasModal: () =>
    Boolean(ui.dialog.value) ||
    shortcutsOpen.value ||
    ui.modals.value.length > 0,
})
</script>
