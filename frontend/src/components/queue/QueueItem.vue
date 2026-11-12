<template>
  <article
    class="flex flex-wrap items-center gap-3 border-b-2 border-line-2 px-3 transition-colors duration-100 sm:px-4"
    :class="[rowClass, compact ? 'min-h-20 py-2' : 'min-h-22 py-3']"
  >
    <CoverArt
      :src="deezerImage(song.cover_url)"
      :name="song.album_name || song.name"
      :letter-size="11"
      :icon-size="13"
      class="size-10"
    />
    <div class="min-w-0 flex-1">
      <div class="flex min-w-0 items-center gap-2">
        <span class="truncate text-[15px] font-medium">{{ song.name }}</span>
        <SourceBadge
          v-if="item.provider"
          :source="item.provider"
          :compact="compact"
        />
      </div>
      <p class="truncate text-[13px] leading-snug text-muted">
        {{ artists
        }}<span v-if="song.album_name"> · {{ song.album_name }}</span>
      </p>
      <p v-if="tech" class="mono truncate text-faint">{{ tech }}</p>
      <p
        v-if="item.state === 'failed'"
        class="mt-1 flex min-w-0 items-start gap-1.5 text-[12px] text-danger"
      >
        <span
          class="mono inline-flex h-[20px] shrink-0 items-center bg-invert px-1.5 text-[10px] tracking-[0.06em] text-on-invert uppercase"
          >{{ t('queue.tabFailed') }}</span
        >
        <AppIcon name="alert" :size="13" class="mt-0.5 shrink-0" />
        <span class="line-clamp-2">{{ failure }}</span>
      </p>
    </div>

    <div
      v-if="item.state === 'active'"
      class="order-last flex w-full shrink-0 items-center gap-3 sm:order-none sm:w-44"
    >
      <UiProgress
        class="flex-1"
        :value="item.progress"
        :indeterminate="!item.progress"
      />
      <span class="mono tabular w-9 shrink-0 text-right text-fg-3">
        {{ item.progress ? `${Math.round(item.progress)}%` : '' }}
      </span>
    </div>

    <div class="flex shrink-0 items-center gap-1">
      <template v-if="item.state === 'done' && item.filename">
        <UiIconButton
          icon="play"
          :label="t('actions.play')"
          size="sm"
          @click="play"
        />
        <a
          :href="item.web_download_url"
          :download="saveName(item.filename)"
          class="flex size-8 items-center justify-center border-2 border-line-2 text-muted transition-colors duration-100 hover:border-line hover:text-fg"
          :title="t('library.saveToDevice')"
          :aria-label="t('library.saveToDevice')"
        >
          <AppIcon name="download" :size="16" />
        </a>
      </template>
      <UiButton
        v-if="item.state === 'failed'"
        size="sm"
        variant="secondary"
        icon="retry"
        @click="dm.retry(song)"
      >
        {{ t('queue.retry') }}
      </UiButton>
      <UiButton
        v-if="
          auth.isAdmin.value &&
          (item.state === 'failed' || item.state === 'active')
        "
        size="sm"
        variant="secondary"
        :disabled="suspending"
        @click="suspendDownload"
      >
        {{ t('downloadPolicy.block') }}
      </UiButton>
      <UiIconButton
        icon="x"
        :label="t('queue.remove')"
        size="sm"
        @click="dm.remove(song)"
      />
    </div>

    <form
      v-if="item.state === 'failed'"
      class="flex basis-full flex-wrap items-center gap-2"
      @submit.prevent="useLink"
    >
      <label
        class="flex h-9 min-w-0 flex-1 basis-60 items-center gap-2 border-2 border-line-3 px-3 focus-within:border-accent"
      >
        <AppIcon name="link" :size="15" class="text-faint" />
        <span class="sr-only">{{ t('queue.overridePlaceholder') }}</span>
        <input
          v-model="override"
          type="url"
          :placeholder="t('queue.overridePlaceholder')"
          class="mono h-full min-w-0 flex-1 bg-transparent text-fg outline-none placeholder:text-faint"
        />
      </label>
      <UiButton size="sm" variant="ghost" type="submit" :disabled="!override">
        {{ t('queue.useLink') }}
      </UiButton>
      <p v-if="overrideError" class="basis-full text-xs text-danger">
        {{ overrideError }}
      </p>
    </form>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useUi } from '/src/model/ui'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import SourceBadge from '../ui/SourceBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import UiProgress from '../ui/UiProgress.vue'
import { useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useQueuePause } from '/src/model/queuePause'
import { useTrackActions } from '/src/model/trackActions'
// Display only: the job's `cover_url` is what its file gets.
import { deezerImage } from '/src/lib/deezerImage'
import { normalizeTrack } from '/src/lib/library'
import { saveName } from '/src/lib/paths'
import { useI18n } from '/src/i18n'

const props = defineProps({
  item: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})

const { t } = useI18n()
// Codes the server sends for songs it won't download (download policy,
// music trash) instead of a message.
const FAILURE_CODES = {
  download_excluded: 'downloadPolicy.blocked',
  library_trash_excluded: 'trash.downloadBlocked',
}
const failure = computed(() => {
  const message = props.item.message
  if (FAILURE_CODES[message]) return t(FAILURE_CODES[message])
  return message || t('queue.failedGeneric')
})
const auth = useAuth()
const ui = useUi()
const suspending = ref(false)
const dm = useDownloadManager()
const library = useLibrary()
const queuePause = useQueuePause()
const actions = useTrackActions()
const override = ref('')
const overrideError = ref('')

const song = computed(() => props.item.song)

// One row language: a 2px accent edge while downloading, a 2px danger
// edge when it failed - the row itself stays paper.
const rowClass = computed(() =>
  props.item.state === 'failed'
    ? 'border-l-2 border-l-danger bg-surface-2'
    : props.item.state === 'active'
      ? 'border-l-2 border-l-accent bg-surface-2'
      : 'border-l-2 border-l-transparent hover:bg-surface-2'
)

// Technical line: the server's own words, or the job's file name.
const tech = computed(() => {
  const item = props.item
  if (item.state === 'done') return item.filename ? saveName(item.filename) : ''
  if (item.state === 'active' || item.state === 'failed') return item.message
  return queuePause.paused.value
    ? t('queue.statusPaused')
    : t('queue.statusQueued')
})

async function suspendDownload() {
  if (
    !(await ui.confirm({
      title: t('downloadPolicy.confirm'),
      body: t('downloadPolicy.confirmHelp'),
      confirmLabel: t('downloadPolicy.block'),
    }))
  )
    return
  const track = song.value || {}
  suspending.value = true
  try {
    await API.excludeDownload({
      song_id: String(track.song_id || ''),
      name: String(track.name || ''),
      artist: String(track.artist || ''),
      artists: Array.isArray(track.artists) ? track.artists : [],
      album_name: String(track.album_name || ''),
      duration: Number(track.duration) || 0,
    })
    ui.toast(t('downloadPolicy.blocked'))
    window.dispatchEvent(new Event('downtify-download-policy-changed'))
  } catch {
    ui.toast(t('downloadPolicy.error'), { kind: 'error' })
  } finally {
    suspending.value = false
  }
}
const artists = computed(
  () =>
    (song.value.artists || []).join(', ') ||
    song.value.artist ||
    t('common.unknownArtist')
)

function play() {
  const file = props.item.filename
  const track = library.tracksByFile.value.get(file) || normalizeTrack(file)
  actions.play([track], 0, null)
}

function youtubeId(url) {
  const match = String(url || '').match(
    /(?:[?&]v=|youtu\.be\/)([A-Za-z0-9_-]{6,})/
  )
  return match ? match[1] : ''
}

function useLink() {
  const id = youtubeId(override.value)
  if (!id) {
    overrideError.value = t('queue.invalidYoutube')
    return
  }
  overrideError.value = ''
  dm.retryWithAudio(song.value, id)
  override.value = ''
}
</script>
