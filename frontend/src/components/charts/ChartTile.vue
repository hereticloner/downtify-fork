<template>
  <!-- One cell of a flush grid: the 2px rules on its right and bottom edges
       are drawn here, the grid supplies the left one. The rank sits in an
       inverted block on the cover's corner. -->
  <article
    class="group relative flex min-w-0 flex-col border-r-2 border-b-2 border-line bg-surface"
  >
    <div class="relative p-2">
      <RouterLink :to="linkTo" class="block" :aria-label="item.name">
        <CoverArt
          :src="item.cover_url"
          :name="item.name"
          :round="round"
          :icon="icon"
          :letter-size="round ? 40 : 52"
          class="aspect-square w-full"
        >
          <span
            v-if="rank"
            class="mono tabular absolute top-0 left-0 flex h-6 min-w-8 items-center justify-center border-r-2 border-b-2 border-line bg-invert px-1.5 text-on-invert"
            >{{ String(rank).padStart(2, '0') }}</span
          >
        </CoverArt>
      </RouterLink>
      <button
        v-if="downloadable"
        type="button"
        class="play-glow absolute right-3.5 bottom-3.5 flex size-9 items-center justify-center border-2 border-line transition-colors duration-100"
        :class="
          queued
            ? 'border-accent bg-surface text-accent'
            : 'bg-invert text-on-invert hover:bg-fg-3'
        "
        :aria-label="t('actions.downloadItem', { name: item.name })"
        :disabled="queued"
        @click="download"
      >
        <AppIcon
          :name="queued ? 'check' : 'download'"
          :size="18"
          stroke-width="2.2"
        />
      </button>
    </div>
    <RouterLink
      :to="linkTo"
      class="flex min-w-0 flex-1 flex-col gap-1 border-t-2 border-line px-2.5 py-2"
      :class="round ? 'items-center text-center' : ''"
    >
      <span
        class="text-display line-clamp-2 text-[14px] leading-tight font-bold"
        >{{ item.name }}</span
      >
      <span class="mono w-full truncate text-muted">{{ subtitle }}</span>
    </RouterLink>
  </article>
</template>

<script setup>
// A Deezer chart card (album, artist or playlist), styled and wired like
// search's ReleaseCard: a cover that opens the item's /link page, and -
// for kinds /link can turn into a flat downloadable tracklist (album,
// playlist) - a download block over it, same as ReleaseCard's. An artist
// resolves to release summaries, not songs (like ReleaseCard's own
// round/artist tiles), so it only navigates. Chart tracks are the only
// immediately-downloadable kind and use TrackDownPlay instead, not this
// card.
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import { useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'

const props = defineProps({
  item: { type: Object, required: true },
  kind: {
    type: String,
    required: true,
    validator: (value) => ['album', 'artist', 'playlist'].includes(value),
  },
  rank: { type: Number, default: null },
})
const { t } = useI18n()
const dm = useDownloadManager()
const ui = useUi()
const queued = ref(false)

const round = computed(() => props.kind === 'artist')
// An artist resolves to release summaries, not songs - nothing fromURL
// could queue directly, so no download button for it (same reasoning as
// ReleaseCard's own round tiles).
const downloadable = computed(
  () => props.kind === 'album' || props.kind === 'playlist'
)
const linkTo = computed(() => ({
  name: 'Link',
  query: { url: props.item.url },
}))

const icon = computed(
  () => ({ album: 'disc', artist: 'user', playlist: 'playlist' })[props.kind]
)

const subtitle = computed(() => {
  switch (props.kind) {
    case 'artist':
      return t('search.artist')
    case 'album':
      return props.item.artist || ''
    case 'playlist':
      return props.item.owner || t('charts.playlist')
    default:
      return ''
  }
})

async function download() {
  queued.value = true
  try {
    const count = await dm.fromURL(props.item.url)
    ui.toast(t('toast.queuedTracks', { count, name: props.item.name }), {
      kind: 'success',
    })
  } catch (err) {
    queued.value = false
    ui.toast(friendlyError(t, err, 'toast.actionFailed'), {
      kind: 'error',
    })
  }
}
</script>
