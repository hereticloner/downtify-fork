<template>
  <div class="flex flex-col">
    <PageHeader
      :title="t('collections.title')"
      class="border-b-2 border-line"
    />

    <!-- New collection: the name block, then the primary action. -->
    <div
      class="flex flex-col gap-2 border-b-2 border-line px-4 py-3 sm:flex-row sm:items-center"
    >
      <label
        class="flex h-10 min-w-0 flex-1 items-center gap-2 border-2 border-line px-3 transition-colors duration-100 focus-within:border-accent sm:max-w-md"
      >
        <AppIcon name="playlist" :size="15" class="text-faint" />
        <span class="sr-only">{{ t('collections.placeholder') }}</span>
        <input
          v-model="newName"
          type="search"
          :placeholder="t('collections.placeholder')"
          class="h-full min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint"
          @keyup.enter="create"
        />
      </label>
      <UiButton variant="primary" icon="plus" @click="create">
        {{ t('collections.create') }}
      </UiButton>
    </div>

    <Transition name="fade" mode="out-in">
      <div
        v-if="loading"
        class="grid border-l-2 border-line sm:grid-cols-2 xl:grid-cols-3"
        aria-busy="true"
      >
        <div
          v-for="n in 3"
          :key="n"
          class="flex flex-col border-r-2 border-b-2 border-line"
        >
          <UiSkeleton class="aspect-[4/3]" />
          <UiSkeleton class="m-3 h-4 w-1/2" />
          <UiSkeleton class="mx-3 mb-3 h-3 w-1/3" />
        </div>
      </div>

      <div v-else-if="error" class="border-b-2 border-line p-4">
        <UiEmpty
          icon="alert"
          :title="t('library.loadFailed')"
          :body="t('library.loadFailedHint')"
        >
          <UiButton icon="refresh" @click="load">{{
            t('common.retry')
          }}</UiButton>
        </UiEmpty>
      </div>

      <div v-else-if="!collections.length" class="border-b-2 border-line p-4">
        <UiEmpty icon="playlist" :title="t('collections.none')" />
      </div>

      <!-- Cluster grid: flush cards, a four-up mosaic cover each. -->
      <div
        v-else
        class="stagger grid border-l-2 border-line sm:grid-cols-2 xl:grid-cols-3"
      >
        <article
          v-for="col in collections"
          :key="col.name"
          class="flex min-w-0 flex-col border-r-2 border-b-2 border-line transition-colors duration-200 hover:bg-surface-2 motion-reduce:transition-none"
        >
          <div class="relative border-b-2 border-line">
            <CoverArt
              :src="col.cover ? collectionCoverURL(col.name) : ''"
              :covers="collectionCoversFor(col)"
              :name="col.name"
              icon="playlist"
              :letter-size="24"
              :icon-size="28"
              class="aspect-[4/3] w-full"
            />
            <UiBadge
              v-if="col.rules?.length"
              tone="accent"
              class="absolute top-0 right-0 border-b border-l-2 border-line bg-surface"
            >
              {{ t('collections.smart') }}
            </UiBadge>
          </div>

          <div class="flex items-stretch border-b border-line-2">
            <h2
              class="text-display min-w-0 flex-1 truncate px-3 py-2 text-[17px] font-bold"
            >
              {{ col.name }}
            </h2>
            <span
              class="mono tabular flex shrink-0 items-center border-l border-line-2 px-3 text-faint"
              >{{ col.playlists.length }}</span
            >
          </div>

          <p
            v-if="col._analysis"
            class="mono border-b border-line-2 px-3 py-2 text-[11px] text-muted"
          >
            {{
              t('collections.analysisSummary', {
                count: col._analysis.tracks,
                missing: col._analysis.missing_tracks,
                megabytes: formatMegabytes(col._analysis.bytes),
              })
            }}
          </p>

          <label
            class="flex h-9 items-center border-b border-line-2 transition-colors duration-100 focus-within:border-accent"
          >
            <span class="sr-only">{{ t('collections.addPlaylist') }}</span>
            <input
              v-model="col._add"
              type="search"
              list="collection-playlist-names"
              :placeholder="t('collections.addPlaylist')"
              class="h-full min-w-0 flex-1 bg-transparent px-3 text-[13px] outline-none placeholder:text-faint"
              @keyup.enter="add(col)"
            />
          </label>

          <div class="flex flex-1 flex-wrap content-start gap-1 px-3 py-2">
            <template v-if="col.playlists.length">
              <span
                v-for="pl in col.playlists"
                :key="pl"
                class="inline-flex max-w-full items-stretch border border-line-2"
              >
                <router-link
                  :to="{ name: 'Playlist', query: { name: pl } }"
                  class="mono min-w-0 truncate px-1.5 py-1 text-muted transition-colors duration-100 hover:text-fg"
                >
                  {{ pl }}
                </router-link>
                <button
                  type="button"
                  class="mono shrink-0 border-l border-line-2 px-1.5 text-faint transition-colors duration-100 hover:bg-surface-2 hover:text-danger"
                  :aria-label="t('collections.removeItem', { name: pl })"
                  @click="removeMember(col, pl)"
                >
                  ×
                </button>
              </span>
            </template>
            <span v-else class="text-[13px] text-faint">
              {{ t('collections.empty') }}
            </span>
          </div>

          <div class="flex items-stretch gap-1 border-t-2 border-line p-1">
            <UiButton
              size="sm"
              variant="ghost"
              icon="play"
              :disabled="!col.playlists.length"
              @click="playCollection(col)"
            >
              {{ t('collections.play') }}
            </UiButton>
            <UiButton
              v-if="auth.isAdmin.value"
              size="sm"
              variant="ghost"
              icon="plus"
              :disabled="!col.playlists.length"
              @click="queueCollection(col)"
            >
              {{ t('collections.queue') }}
            </UiButton>
            <UiButton
              v-if="missingMembers(col).length"
              size="sm"
              variant="ghost"
              icon="download"
              :loading="downloadingCollection === col.name"
              @click="downloadMissing(col)"
            >
              {{
                t('collections.downloadMissing', { count: missingCount(col) })
              }}
            </UiButton>
            <div class="ml-auto flex items-center gap-1">
              <CollectionCoverPicker
                v-if="auth.isAdmin.value"
                :name="col.name"
                :has-cover="Boolean(col.cover)"
                @changed="load"
              />
              <UiIconButton
                icon="sliders"
                size="sm"
                :label="t('collections.rules')"
                :active="!!col.rules?.length"
                @click="openRules(col)"
              />
              <UiIconButton
                icon="pencil"
                size="sm"
                :label="t('collections.rename')"
                @click="openRename(col)"
              />
              <UiIconButton
                icon="trash"
                size="sm"
                :label="t('common.delete')"
                @click="remove(col)"
              />
            </div>
          </div>
        </article>
      </div>
    </Transition>

    <datalist id="collection-playlist-names">
      <option v-for="name in playlistNames" :key="name" :value="name" />
    </datalist>

    <UiModal
      :open="renameOpen"
      :title="t('collections.renameTitle')"
      :description="t('collections.renameHint')"
      @close="closeRename"
    >
      <form class="flex flex-col gap-4" @submit.prevent="submitRename">
        <UiInput
          v-model="renameDraft"
          :label="t('collections.name')"
          :placeholder="t('collections.namePlaceholder')"
          icon="playlist"
        />
      </form>
      <template #footer>
        <UiButton variant="ghost" @click="closeRename">{{
          t('common.cancel')
        }}</UiButton>
        <UiButton
          variant="primary"
          icon="pencil"
          :disabled="!canRename"
          :loading="renaming"
          @click="submitRename"
        >
          {{ t('collections.rename') }}
        </UiButton>
      </template>
    </UiModal>

    <UiModal
      :open="rulesOpen"
      :title="t('collections.rulesTitle')"
      :description="t('collections.rulesHint')"
      width="sm:max-w-xl"
      @close="closeRules"
    >
      <CollectionRuleEditor v-model="rulesDraft" />
      <div v-if="rulesPreview" class="border-2 border-line-2 p-3 text-[13px]">
        <p class="font-medium">{{ t('collections.previewTitle') }}</p>
        <p class="mt-1 text-muted">
          {{
            t('collections.previewCount', {
              count: rulesPreview.playlists.length,
            })
          }}
        </p>
        <ul
          v-if="rulesPreview.playlists.length"
          class="mono mt-2 flex flex-wrap gap-1"
        >
          <li
            v-for="name in rulesPreview.playlists"
            :key="name"
            class="border border-line-2 px-1.5 py-1 text-muted"
          >
            {{ name }}
          </li>
        </ul>
      </div>
      <template #footer>
        <UiButton variant="ghost" @click="closeRules">{{
          t('common.cancel')
        }}</UiButton>
        <UiButton
          variant="secondary"
          :loading="previewingRules"
          @click="previewRules"
        >
          {{ t('collections.preview') }}
        </UiButton>
        <UiButton
          variant="primary"
          icon="check"
          :loading="savingRules"
          @click="submitRules"
        >
          {{ t('collections.saveRules') }}
        </UiButton>
      </template>
    </UiModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '/src/i18n'
import PageHeader from '/src/components/library/PageHeader.vue'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import { useLibrary } from '/src/model/library'
import { useAuth } from '/src/model/auth'
import { usePlayer } from '/src/model/player'
import { useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import CollectionCoverPicker from '/src/components/collections/CollectionCoverPicker.vue'
import CollectionRuleEditor from '/src/components/collections/CollectionRuleEditor.vue'
import {
  collectionCoverURL,
  createCollection,
  deleteCollection,
  downloadCollectionMissing,
  editCollectionItems,
  getCollectionAnalysis,
  getCollectionTracks,
  listCollections,
  previewCollectionRules,
  removeCollectionItem,
  renameCollection,
  saveCollectionRules,
} from '/src/model/collections'
import { cleanRules, ruleNodesFromSaved } from '/src/lib/collectionRules'
import {
  collectionMissingCount,
  collectionMissingPlaylists,
} from '/src/lib/collectionMissing'
import { collectionCovers } from '/src/lib/mosaic'
import { friendlyError } from '/src/lib/errors'
import { canSubmitRename } from '/src/lib/rename'

const { t } = useI18n()
const library = useLibrary()
const auth = useAuth()
const player = usePlayer()
const dm = useDownloadManager()
const ui = useUi()
const router = useRouter()
const collections = ref([])
const newName = ref('')
const error = ref(false)
const loading = ref(true)
const downloadingCollection = ref('')

// Names offered by the "add a playlist" box's native autocomplete - the
// same playlist list the Library page shows, so a name can't be typo'd.
const playlistNames = computed(() =>
  library.playlists.value
    .map((playlist) => String(playlist?.name || ''))
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b))
)

// The card's mosaic: one cover per member playlist, in the collection's
// order, so a collection reads as the artwork it groups. Empty when
// nothing is showable — CoverArt then falls back to the name's initials.
function collectionCoversFor(col) {
  return collectionCovers(col.playlists, library.playlists.value)
}

// The member playlists that still have tracks to download. A collection
// with none hides the "download missing" action entirely.
function missingMembers(col) {
  return collectionMissingPlaylists(col.playlists, library.playlists.value)
}

function missingCount(col) {
  return collectionMissingCount(col.playlists, library.playlists.value)
}

// Queue every missing member through the existing per-playlist endpoint
// and report the total once, using the same toast the Queue page shows.
async function downloadMissing(col) {
  const members = missingMembers(col)
  if (!members.length) return
  downloadingCollection.value = col.name
  try {
    const count = await downloadCollectionMissing(members)
    if (count) {
      ui.toast(t('toast.queuedMissing', { count }), {
        kind: 'success',
        action: {
          label: t('nav.queue'),
          run: () => router.push({ name: 'Queue' }),
        },
      })
    } else {
      ui.toast(t('toast.playlistComplete'), { kind: 'success' })
    }
    library.refreshSoon(500)
  } catch (err) {
    failed(err)
  } finally {
    downloadingCollection.value = ''
  }
}

function formatMegabytes(bytes) {
  return (Number(bytes || 0) / 1024 / 1024).toFixed(1)
}

async function playCollection(col) {
  try {
    const data = await getCollectionTracks(col.name)
    player.playList(data.tracks || [], {
      context: { type: 'collection', name: col.name },
    })
  } catch (err) {
    failed(err)
  }
}

async function queueCollection(col) {
  try {
    const data = await getCollectionTracks(col.name)
    await dm.fromSongs(data.tracks || [], { playlistName: col.name })
    ui.toast(t('collections.queued'), { kind: 'success' })
  } catch (err) {
    failed(err)
  }
}

function failed(err) {
  ui.toast(friendlyError(t, err, 'toast.actionFailed'), { kind: 'error' })
}

async function load() {
  loading.value = true
  error.value = false
  try {
    collections.value = await Promise.all(
      (await listCollections()).map(async (c) => ({
        ...c,
        _add: '',
        _analysis: await getCollectionAnalysis(c.name).catch(() => null),
      }))
    )
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!newName.value.trim()) return
  try {
    await createCollection(newName.value)
    newName.value = ''
    await load()
  } catch (err) {
    failed(err)
  }
}

async function add(col) {
  if (!col._add.trim()) return
  try {
    await editCollectionItems(col.name, { add: [col._add] })
    col._add = ''
    await load()
  } catch (err) {
    failed(err)
  }
}

async function removeMember(col, playlist) {
  try {
    await removeCollectionItem(col.name, playlist)
    await load()
    if (col.rules?.length) {
      ui.toast(t('collections.smartMayReturn'), { kind: 'info' })
    }
  } catch (err) {
    failed(err)
  }
}

async function remove(col) {
  const confirmed = await ui.confirm({
    title: t('collections.confirmDelete', { name: col.name }),
    confirmLabel: t('common.delete'),
    danger: true,
  })
  if (!confirmed) return
  try {
    await deleteCollection(col.name)
    await load()
  } catch (err) {
    failed(err)
  }
}

// Renaming keeps the playlists: it is the collection's own name only.
const renameOpen = ref(false)
const renameTarget = ref(null)
const renameDraft = ref('')
const renaming = ref(false)
const canRename = computed(() =>
  canSubmitRename(renameTarget.value?.name, renameDraft.value, renaming.value)
)

function openRename(col) {
  renameTarget.value = col
  renameDraft.value = col.name
  renameOpen.value = true
}

function closeRename() {
  renameOpen.value = false
  renameTarget.value = null
}

async function submitRename() {
  const col = renameTarget.value
  const name = renameDraft.value.trim()
  if (!col || !name || !canRename.value) return
  renaming.value = true
  try {
    await renameCollection(col.name, name)
    ui.toast(t('collections.renamed', { name }), { kind: 'success' })
    closeRename()
    await load()
  } catch (err) {
    failed(err)
  } finally {
    renaming.value = false
  }
}

// Smart rules: the editor holds a tree of conditions/groups; saving
// replaces the whole rule list, and an empty tree makes it static.
const rulesOpen = ref(false)
const rulesTarget = ref(null)
const rulesDraft = ref([])
const rulesPreview = ref(null)
const savingRules = ref(false)
const previewingRules = ref(false)

function openRules(col) {
  rulesTarget.value = col
  rulesDraft.value = ruleNodesFromSaved(col.rules)
  rulesPreview.value = null
  rulesOpen.value = true
}

function closeRules() {
  rulesOpen.value = false
  rulesTarget.value = null
  rulesDraft.value = []
  rulesPreview.value = null
}

async function previewRules() {
  const col = rulesTarget.value
  if (!col) return
  previewingRules.value = true
  try {
    rulesPreview.value = await previewCollectionRules(
      col.name,
      cleanRules(rulesDraft.value)
    )
  } catch (err) {
    failed(err)
  } finally {
    previewingRules.value = false
  }
}

async function submitRules() {
  const col = rulesTarget.value
  if (!col) return
  savingRules.value = true
  try {
    await saveCollectionRules(col.name, cleanRules(rulesDraft.value))
    ui.toast(t('collections.rulesSaved'), { kind: 'success' })
    closeRules()
    await load()
  } catch (err) {
    failed(err)
  } finally {
    savingRules.value = false
  }
}

onMounted(() => {
  library.load()
  load()
})
</script>
