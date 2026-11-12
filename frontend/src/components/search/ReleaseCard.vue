<template>
  <!-- A search result cell: framed cover, mono release label, catalogue line
       under it, and the download block sitting on the artwork's corner. -->
  <article
    class="group relative flex min-w-0 flex-col border-r-2 border-b-2 border-line bg-surface"
  >
    <div class="relative p-2">
      <RouterLink :to="linkTo" class="block" :aria-label="release.name">
        <CoverArt
          :src="deezerImage(release.cover_url)"
          :name="release.name"
          :round="round"
          :icon="round ? 'user' : 'disc'"
          :letter-size="round ? 40 : 52"
          class="aspect-square w-full"
        >
          <span
            v-if="typeLabel"
            class="eyebrow absolute top-0 left-0 border-r-2 border-b-2 border-line bg-surface px-1.5 py-0.5 text-fg-3"
            >{{ typeLabel }}</span
          >
        </CoverArt>
      </RouterLink>
      <button
        v-if="!round"
        type="button"
        class="absolute right-3.5 bottom-3.5 flex size-9 items-center justify-center border-2 border-line transition-colors duration-100"
        :class="
          queued
            ? 'border-accent bg-surface text-accent'
            : 'bg-invert text-on-invert hover:bg-fg-3'
        "
        :aria-label="t('actions.downloadItem', { name: release.name })"
        :disabled="queued"
        @click="download"
      >
        <AppIcon
          :name="queued ? 'check' : 'download'"
          :size="15"
          stroke-width="2"
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
        >{{ release.name }}</span
      >
      <span class="mono w-full truncate text-muted">{{ subtitle }}</span>
    </RouterLink>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
// Display only (a Deezer cover at its medium size); the download below
// resolves the release's own link, never this image.
import { deezerImage } from '/src/lib/deezerImage'
import { useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'

const props = defineProps({
  release: { type: Object, required: true },
  round: { type: Boolean, default: false },
  // Where the card opens; by default the release's link, resolved like a
  // pasted one (the Link page).
  to: { type: [String, Object], default: null },
})
const { t } = useI18n()
const dm = useDownloadManager()
const ui = useUi()
const queued = ref(false)

const linkTo = computed(
  () =>
    props.to || {
      name: 'Link',
      query: { url: props.release.url },
    }
)

const typeLabel = computed(() => {
  const type = String(props.release.release_type || '').toLowerCase()
  if (!type || props.round) return ''
  const known = {
    album: t('search.typeAlbum'),
    single: t('search.typeSingle'),
    ep: t('search.typeEp'),
  }
  return known[type] || props.release.release_type
})

const subtitle = computed(() => {
  if (props.round) return t('search.artist')
  return [props.release.artist, props.release.year].filter(Boolean).join(' · ')
})

async function download() {
  queued.value = true
  try {
    const count = await dm.fromURL(props.release.url)
    ui.toast(t('toast.queuedTracks', { count, name: props.release.name }), {
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
