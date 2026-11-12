<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('discover.title')"
      :subtitle="t('discover.subtitle')"
      class="border-b-2 border-line"
    >
      <UiButton variant="secondary" icon="eye" @click="hiddenOpen = true">
        {{
          t('discover.hiddenButton', { count: discover.blocked.value.length })
        }}
      </UiButton>
      <UiButton
        icon="refresh"
        :loading="discover.loading.value"
        :disabled="!canSuggest"
        @click="refresh"
      >
        {{ t('discover.refresh') }}
      </UiButton>
    </PageHeader>

    <div
      v-if="!library.loaded.value || (discover.loading.value && !items.length)"
      class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      aria-busy="true"
    >
      <div
        v-for="n in 12"
        :key="n"
        class="flex flex-col gap-2 border-r-2 border-b-2 border-line p-2"
      >
        <UiSkeleton class="aspect-square w-full" />
        <UiSkeleton class="h-3 w-3/4" />
        <UiSkeleton class="h-2.5 w-1/2" />
      </div>
    </div>

    <div v-else-if="!canSuggest" class="border-b-2 border-line p-4">
      <UiEmpty
        icon="sparkle"
        :title="t('discover.emptyLibraryTitle')"
        :body="t('discover.emptyLibraryBody')"
      >
        <UiButton icon="search" :to="{ name: 'Search' }">
          {{ t('discover.findMusic') }}
        </UiButton>
      </UiEmpty>
    </div>

    <div
      v-else-if="discover.error.value && !items.length"
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="alert"
        :title="t('discover.failed')"
        :body="discover.error.value"
      >
        <UiButton icon="refresh" @click="refresh">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div
      v-else-if="discover.loaded.value && !items.length"
      class="border-b-2 border-line p-4"
    >
      <UiEmpty
        icon="sparkle"
        :title="t('discover.noneTitle')"
        :body="t('discover.noneBody')"
      />
    </div>

    <div
      v-else-if="items.length"
      class="grid xl:grid-cols-[minmax(0,1fr)_340px]"
    >
      <div class="flex min-w-0 flex-col">
        <!-- Suggested artists: four to a row, flush -->
        <section class="flex flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <span
              class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
              >01</span
            >
            <h2
              class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
            >
              {{ t('discover.artistsTitle') }}
            </h2>
            <UiButton
              v-if="items.length > ARTISTS_SHOWN"
              variant="ghost"
              size="sm"
              class="my-1 mr-1 border-line-2"
              @click="showAllArtists = !showAllArtists"
            >
              {{
                showAllArtists
                  ? t('discover.showLess')
                  : t('discover.showAll', { count: items.length })
              }}
            </UiButton>
            <span
              class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
              >{{ items.length }}</span
            >
          </div>
          <div :class="ARTIST_GRID">
            <MediaTile
              v-for="item in shownArtists"
              :key="item.name"
              :to="artistRoute(item)"
              :title="item.name"
              :subtitle="because(item)"
              v-bind="artistPhoto(item)"
              :name="item.name"
              icon="user"
              round
              :playable="false"
            >
              <template #overlay>
                <UiMenu
                  :items="menuFor(item)"
                  :label="t('discover.moreFor', { name: item.name })"
                >
                  <template #trigger>
                    <button
                      type="button"
                      class="flex size-8 items-center justify-center border-2 border-line bg-bg text-fg transition-colors duration-100 hover:bg-surface-2 active:bg-raised"
                      :aria-label="t('discover.moreFor', { name: item.name })"
                    >
                      <AppIcon name="more" :size="16" />
                    </button>
                  </template>
                </UiMenu>
              </template>
            </MediaTile>
          </div>
        </section>

        <!-- Album and playlist shelves: the same flush grid under a ruled
             header, with the shelf's note in mono under the title. -->
        <section
          v-for="(shelf, i) in shelves"
          :key="shelf.id"
          class="flex flex-col"
        >
          <div class="border-b-2 border-line bg-surface-2">
            <div class="flex items-stretch">
              <span
                class="mono flex w-10 shrink-0 items-center justify-center border-r-2 border-line text-faint"
                >0{{ i + 2 }}</span
              >
              <h2
                class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
              >
                {{ shelf.title }}
              </h2>
              <span
                class="mono flex shrink-0 items-center border-l-2 border-line px-3 text-faint"
                >{{ shelf.items.length }}</span
              >
            </div>
            <p
              class="border-t border-line-2 px-3 py-1.5 text-[12px] text-muted"
            >
              {{ shelf.body }}
            </p>
          </div>
          <div
            v-if="shelf.loading && !shelf.items.length"
            class="grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
            aria-busy="true"
          >
            <div
              v-for="n in 6"
              :key="n"
              class="flex flex-col gap-2 border-r-2 border-b-2 border-line p-2"
            >
              <UiSkeleton class="aspect-square w-full" />
              <UiSkeleton class="h-3 w-3/4" />
            </div>
          </div>
          <div
            v-else
            :class="SHELF_GRID"
            :aria-busy="shelf.pending || undefined"
          >
            <MediaTile
              v-for="item in shelf.items"
              :key="item.key || item.url"
              :to="collectionRoute(item)"
              :title="item.name"
              :subtitle="shelf.subtitle(item)"
              :cover="item.cover_url"
              :name="item.name"
              :icon="shelf.icon"
              :playable="false"
            >
              <!-- Which service it's from. A Deezer album opens in the
                   Finder, a Spotify one - and any playlist - on its Link
                   page. -->
              <template v-if="shelf.badge && item.source" #badge>
                <span
                  class="absolute top-0 right-0 flex h-6 items-center gap-1 border-b-2 border-l-2 border-line bg-surface px-1.5"
                  :class="
                    item.source === 'spotify' ? 'text-spotify' : 'text-deezer'
                  "
                  :title="
                    t('discover.onPlatform', { name: platformName(item) })
                  "
                >
                  <AppIcon :name="item.source" :size="12" />
                  <span class="sr-only">{{
                    t('discover.onPlatform', { name: platformName(item) })
                  }}</span>
                </span>
              </template>
            </MediaTile>
            <!-- Spotify's suggestions are still on their way: they'll be
                 added here, at the end. -->
            <template v-if="shelf.pending">
              <div
                v-for="n in 2"
                :key="`pending-${n}`"
                class="flex flex-col gap-2 border-r-2 border-b-2 border-line p-2"
              >
                <UiSkeleton class="aspect-square w-full" />
                <UiSkeleton class="h-3 w-3/4" />
              </div>
            </template>
          </div>
        </section>

        <p class="px-3 py-2 text-[11px] text-faint">
          {{ t('discover.poweredBy') }}
        </p>
      </div>

      <!-- Apparatus: what the suggestions are made of, and what is held
           back. -->
      <aside class="flex min-w-0 flex-col xl:border-l-2 xl:border-line">
        <p
          v-if="discover.partial.value"
          class="flex items-center gap-2 border-b-2 border-line px-3 py-2 text-[12px] text-muted"
          role="status"
        >
          <AppIcon name="info" :size="14" class="shrink-0 text-faint" />
          {{ t('discover.partial') }}
        </p>
        <p
          v-if="discover.collectionsError.value"
          class="flex items-center gap-2 border-b-2 border-line px-3 py-2 text-[12px] text-muted"
          role="status"
        >
          <AppIcon name="info" :size="14" class="shrink-0 text-faint" />
          {{ t('discover.collectionsFailed') }}
        </p>

        <section class="flex flex-col">
          <div class="flex items-stretch border-b-2 border-line bg-surface-2">
            <h2
              class="eyebrow flex min-w-0 flex-1 items-center px-3 py-2 text-fg"
            >
              {{ t('discover.hiddenTitle') }}
            </h2>
            <UiButton
              variant="ghost"
              size="sm"
              class="my-1 mr-1 border-line-2"
              @click="hiddenOpen = true"
            >
              {{ t('discover.hide') }}
            </UiButton>
          </div>
          <ul v-if="discover.blocked.value.length" class="flex flex-col px-3">
            <li
              v-for="row in discover.blocked.value"
              :key="row.name"
              class="mono flex items-center gap-2 border-b border-line-2 py-1.5 last:border-b-0"
            >
              <span class="size-2 shrink-0 bg-line-3" aria-hidden="true" />
              <span class="min-w-0 flex-1 truncate text-fg-3">{{
                row.name
              }}</span>
              <button
                type="button"
                class="eyebrow shrink-0 text-muted transition-colors duration-100 hover:text-fg"
                @click="unhide(row.name)"
              >
                {{ t('discover.unhide') }}
              </button>
            </li>
          </ul>
          <p v-else class="mono px-3 py-2 text-faint">
            {{ t('discover.hiddenEmpty') }}
          </p>
        </section>
      </aside>
    </div>

    <UiModal
      :open="hiddenOpen"
      :title="t('discover.hiddenTitle')"
      :description="t('discover.hiddenBody')"
      @close="hiddenOpen = false"
    >
      <div class="flex flex-col gap-4 px-5 py-4 sm:px-6">
        <form class="flex items-end gap-2" @submit.prevent="blockTyped">
          <UiInput
            v-model="typedName"
            class="min-w-0 flex-1"
            :label="t('discover.hideByName')"
            :placeholder="t('discover.hideByNamePlaceholder')"
          />
          <UiButton type="submit" icon="plus" :disabled="!typedName.trim()">
            {{ t('discover.hide') }}
          </UiButton>
        </form>

        <ul v-if="discover.blocked.value.length" class="flex flex-col">
          <li
            v-for="row in discover.blocked.value"
            :key="row.name"
            class="flex items-center gap-3 border-b border-line-2 py-2 last:border-b-0"
          >
            <CoverArt
              :src="proxiedArtistPhotoUrl(row.name)"
              :name="row.name"
              icon="user"
              round
              :letter-size="14"
              class="size-10"
            />
            <span class="mono min-w-0 flex-1 truncate text-fg">{{
              row.name
            }}</span>
            <UiButton size="sm" variant="ghost" @click="unhide(row.name)">
              {{ t('discover.unhide') }}
            </UiButton>
          </li>
        </ul>
        <p v-else class="mono text-faint">{{ t('discover.hiddenEmpty') }}</p>

        <div class="flex flex-col gap-2 border-t-2 border-line pt-4">
          <p class="text-[13px] text-muted">{{ t('discover.listensBody') }}</p>
          <div>
            <UiButton
              size="sm"
              variant="ghost"
              icon="trash"
              @click="forgetListens"
            >
              {{ t('discover.clearListens') }}
            </UiButton>
          </div>
        </div>
      </div>
    </UiModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import { useDiscover } from '/src/model/discover'
import { useLibrary } from '/src/model/library'
import { useLikes } from '/src/model/likes'
import { useUi } from '/src/model/ui'
import {
  artistRoute,
  collectionRoute,
  collectionsPayload,
  deezerArtistUrl,
  findSongsLocation,
  joinNames,
  libraryPayload,
} from '/src/lib/discover'
import {
  knownArtistPhoto,
  proxiedArtistPhotoUrl,
} from '/src/lib/artistPhotoProxy'
import { deezerImage } from '/src/lib/deezerImage'
import { useI18n } from '/src/i18n'
import { useRouter } from 'vue-router'

const { t, locale } = useI18n()
const router = useRouter()
const ui = useUi()
const library = useLibrary()
const likes = useLikes()
const discover = useDiscover()

// Flush grids: every cell draws its own right/bottom rule, the grid (or the
// section header above it) the left one.
const ARTIST_GRID =
  'grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4'
const SHELF_GRID =
  'grid grid-cols-2 border-l-2 border-line sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6'
// Artists shown before "Show all": two rows on a wide screen.
const ARTISTS_SHOWN = 12

const items = computed(() => discover.items.value)
const canSuggest = computed(() => library.artists.value.length > 0)
const showAllArtists = ref(false)
const shownArtists = computed(() =>
  showAllArtists.value ? items.value : items.value.slice(0, ARTISTS_SHOWN)
)

const PLATFORMS = { deezer: 'Deezer', spotify: 'Spotify' }

// A suggested artist's photo: a saved one when the library has it, else
// the Deezer picture the suggestion came with (medium size) - relayed by
// the photo proxy without a search by name, and loaded directly if the
// proxy can't answer. As MediaTile's `cover`/`fallback`.
function artistPhoto(item) {
  return knownArtistPhoto(item.name, deezerImage(item.picture_url))
}

function platformName(item) {
  return PLATFORMS[item.source] || item.source
}

// Deezer's answer fills the shelves (`loading` until it comes); Spotify's
// is added at the end of each (`pending` until then).
const shelves = computed(() => {
  const deezerLoading = discover.collectionsLoading.value
  const spotifyLoading = discover.spotifyLoading.value
  const albumSubtitle = (item) =>
    [item.artist, item.year].filter(Boolean).join(' · ')
  const playlistSubtitle = (item) =>
    t('discover.essentialsOf', { name: item.artist })
  return [
    {
      id: 'albums',
      title: t('discover.albumsTitle'),
      body: t('discover.albumsBody'),
      icon: 'disc',
      badge: true,
      items: discover.albums.value,
      subtitle: albumSubtitle,
      loading: deezerLoading,
      pending: !deezerLoading && spotifyLoading,
    },
    {
      id: 'more',
      title: t('discover.moreAlbumsTitle'),
      body: t('discover.moreAlbumsBody'),
      icon: 'disc',
      badge: true,
      items: discover.moreAlbums.value,
      subtitle: albumSubtitle,
      loading: deezerLoading,
      pending: !deezerLoading && spotifyLoading,
    },
    {
      // Deezer's "100%" playlists, then Spotify's "This Is" added at the
      // end as they come - each with its service on the cover.
      id: 'playlists',
      title: t('discover.playlistsTitle'),
      body: t('discover.playlistsBody'),
      icon: 'playlist',
      badge: true,
      items: [
        ...discover.deezerPlaylists.value,
        ...discover.spotifyPlaylists.value,
      ],
      subtitle: playlistSubtitle,
      loading: deezerLoading,
      pending: !deezerLoading && spotifyLoading,
    },
  ].filter((shelf) => shelf.items.length || shelf.loading || shelf.pending)
})

const hiddenOpen = ref(false)
const typedName = ref('')

async function refresh() {
  if (!canSuggest.value) return
  await discover.load(libraryPayload(library.artists.value, likes.liked.value))
  // Built on the artists just ranked (cached on the server), so after them.
  discover.loadCollections(
    collectionsPayload(
      library.artists.value,
      library.albums.value,
      library.playlists.value,
      likes.liked.value
    )
  )
}

function because(item) {
  return item.because?.length
    ? t('discover.because', { names: joinNames(item.because, locale.value) })
    : ''
}

function menuFor(item) {
  const deezerUrl = deezerArtistUrl(item)
  return [
    {
      label: t('discover.findSongs'),
      icon: 'search',
      action: () => router.push(findSongsLocation(item)),
    },
    {
      label: t('discover.openDeezer'),
      icon: 'deezer',
      hidden: !deezerUrl,
      action: () => window.open(deezerUrl, '_blank', 'noopener'),
    },
    { divider: true },
    {
      label: t('discover.notInterested'),
      icon: 'x',
      danger: true,
      action: () => hide(item.name),
    },
  ]
}

async function hide(name) {
  if (await discover.block(name)) {
    ui.toast(t('discover.hidden', { name }), {
      action: { label: t('discover.undo'), run: () => unhide(name) },
    })
  } else {
    ui.toast(t('discover.actionFailed'), { kind: 'error' })
  }
}

async function unhide(name) {
  if (await discover.unblock(name)) refresh()
  else ui.toast(t('discover.actionFailed'), { kind: 'error' })
}

async function blockTyped() {
  const name = typedName.value.trim()
  if (!name) return
  if (await discover.block(name)) typedName.value = ''
  else ui.toast(t('discover.actionFailed'), { kind: 'error' })
}

async function forgetListens() {
  const ok = await ui.confirm({
    title: t('discover.clearListensTitle'),
    body: t('discover.clearListensBody'),
    confirmLabel: t('discover.clearListens'),
    danger: true,
  })
  if (!ok) return
  if (await discover.clearListens()) {
    ui.toast(t('discover.listensCleared'), { kind: 'success' })
    refresh()
  } else {
    ui.toast(t('discover.actionFailed'), { kind: 'error' })
  }
}

onMounted(() => {
  library.ensureArtists()
  library.ensureAlbums()
  discover.loadBlocked()
})

// First visit: suggest as soon as the library is known. Coming back keeps
// the last list (the server caches Deezer's answers for a week anyway).
watch(
  () => [library.artistsComplete.value, library.albumsComplete.value],
  ([artistsReady]) => {
    if (artistsReady && !discover.loaded.value) refresh()
  },
  { immediate: true }
)
</script>
