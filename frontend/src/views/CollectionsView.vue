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
        class="flex min-w-0 flex-col border-r-2 border-b-2 border-line"
      >
        <div class="relative border-b-2 border-line">
          <CoverArt
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
            <router-link
              v-for="pl in col.playlists"
              :key="pl"
              :to="{ name: 'Playlist', query: { name: pl } }"
              class="mono max-w-full truncate border border-line-2 px-1.5 py-1 text-muted transition-colors duration-100 hover:border-line hover:text-fg"
            >
              {{ pl }}
            </router-link>
          </template>
          <span v-else class="text-[13px] text-faint">
            {{ t('collections.empty') }}
          </span>
        </div>

        <div class="flex items-stretch gap-1 border-t-2 border-line p-1">
          <UiButton
            v-if="missingMembers(col).length"
            size="sm"
            variant="ghost"
            icon="download"
            :loading="downloadingCollection === col.name"
            @click="downloadMissing(col)"
          >
            {{ t('collections.downloadMissing', { count: missingCount(col) }) }}
          </UiButton>
          <div class="ml-auto flex items-center gap-1">
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
      <div class="flex flex-col gap-2">
        <div
          v-for="(rule, index) in rulesDraft"
          :key="index"
          class="flex flex-col gap-2 border-2 border-line-2 p-3 sm:flex-row sm:items-end"
        >
          <UiSelect
            :model-value="rule.type"
            :options="rulesTypeOptions"
            :label="t('collections.ruleType')"
            block
            class="sm:w-40"
            @update:model-value="onTypeChange(rule, $event)"
          />
          <template v-if="rule.type === 'added'">
            <UiInput
              v-model="rule.from"
              type="date"
              :label="t('collections.ruleFrom')"
            />
            <UiInput
              v-model="rule.to"
              type="date"
              :label="t('collections.ruleTo')"
            />
          </template>
          <template v-else-if="rule.type === 'plays'">
            <UiInput
              v-model="rule.min"
              type="number"
              min="0"
              inputmode="numeric"
              :label="t('collections.ruleMin')"
            />
            <UiInput
              v-model="rule.max"
              type="number"
              min="0"
              inputmode="numeric"
              :label="t('collections.ruleMax')"
            />
          </template>
          <UiInput
            v-else
            v-model="rule.value"
            :label="t('collections.ruleValue')"
            :placeholder="t('collections.ruleValuePlaceholder')"
          />
          <UiIconButton
            icon="trash"
            :label="t('common.delete')"
            class="self-end"
            @click="removeRule(index)"
          />
        </div>
        <p v-if="!rulesDraft.length" class="mono text-faint">
          {{ t('collections.noRules') }}
        </p>
        <UiButton variant="ghost" icon="plus" @click="addRule">
          {{ t('collections.addRule') }}
        </UiButton>
      </div>
      <template #footer>
        <UiButton variant="ghost" @click="closeRules">{{
          t('common.cancel')
        }}</UiButton>
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
import { useUi } from '/src/model/ui'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import {
  createCollection,
  deleteCollection,
  downloadCollectionMissing,
  editCollectionItems,
  listCollections,
  renameCollection,
  saveCollectionRules,
} from '/src/model/collections'
import { RULE_TYPES, blankRule, cleanRules } from '/src/lib/collectionRules'
import {
  collectionMissingCount,
  collectionMissingPlaylists,
} from '/src/lib/collectionMissing'
import { collectionCovers } from '/src/lib/mosaic'
import { friendlyError } from '/src/lib/errors'
import { canSubmitRename } from '/src/lib/rename'

// Label keys for the rule-type picker, one per type the API understands.
const RULE_LABEL_KEYS = {
  added: 'collections.ruleAdded',
  plays: 'collections.rulePlays',
  genre: 'collections.ruleGenre',
  artist: 'collections.ruleArtist',
  album: 'collections.ruleAlbum',
  format: 'collections.ruleFormat',
}

const { t } = useI18n()
const library = useLibrary()
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

function failed(err) {
  ui.toast(friendlyError(t, err, 'toast.actionFailed'), { kind: 'error' })
}

async function load() {
  loading.value = true
  error.value = false
  try {
    collections.value = (await listCollections()).map((c) => ({
      ...c,
      _add: '',
    }))
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

// Smart rules: the editor holds a draft row per rule; saving replaces the
// collection's whole rule list, so clearing every row makes it static.
const rulesOpen = ref(false)
const rulesTarget = ref(null)
const rulesDraft = ref([])
const savingRules = ref(false)

const rulesTypeOptions = computed(() =>
  RULE_TYPES.map((type) => ({
    value: type,
    label: t(RULE_LABEL_KEYS[type]),
  }))
)

function openRules(col) {
  rulesTarget.value = col
  rulesDraft.value = (col.rules || []).map((rule) => ({ ...rule }))
  rulesOpen.value = true
}

function closeRules() {
  rulesOpen.value = false
  rulesTarget.value = null
  rulesDraft.value = []
}

function addRule() {
  rulesDraft.value.push(blankRule())
}

function removeRule(index) {
  rulesDraft.value.splice(index, 1)
}

// Switching a row's type resets its fields to the new type's blanks, so a
// leftover value can't leak into an unrelated rule.
function onTypeChange(rule, type) {
  if (rule.type === type) return
  const fresh = blankRule(type)
  for (const key of Object.keys(rule)) delete rule[key]
  Object.assign(rule, fresh)
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
