<template>
  <Transition name="fade">
    <!-- Sticks under the shell's fixed chrome: the 44px masthead on a phone
         (the nav strip only appears from md up), then the 48px masthead plus
         the 40px strip. No gap, so no row slips through above the bar. -->
    <div
      v-if="count"
      class="sticky top-[calc(2.75rem+env(safe-area-inset-top))] z-20 flex flex-wrap items-center gap-2 border-2 border-line bg-surface-2 p-2 pl-3 md:top-[calc(5.5rem+env(safe-area-inset-top))]"
    >
      <span class="mono tabular text-fg">
        {{ t('library.selectedCount', { count }) }}
      </span>
      <button
        v-if="count < total"
        type="button"
        class="eyebrow border-b border-line-2 pb-0.5 text-accent transition-colors duration-100 hover:border-accent"
        @click="$emit('select-all')"
      >
        {{ t('library.selectAllCount', { count: total }) }}
      </button>
      <div class="ml-auto flex flex-wrap items-center gap-1.5">
        <UiButton
          size="sm"
          variant="secondary"
          icon="play"
          @click="$emit('play')"
        >
          <span class="max-sm:sr-only">{{ t('actions.play') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="secondary"
          icon="queue"
          @click="$emit('enqueue')"
        >
          <span class="max-sm:sr-only">{{ t('actions.addToQueue') }}</span>
        </UiButton>
        <UiButton
          v-if="auth.isAdmin.value"
          size="sm"
          variant="secondary"
          icon="playlist"
          @click="$emit('add-to-playlist')"
        >
          <span class="max-sm:sr-only">{{ t('actions.addToPlaylist') }}</span>
        </UiButton>
        <UiButton
          size="sm"
          variant="secondary"
          icon="zip"
          :loading="zipping"
          @click="$emit('zip')"
        >
          <span class="max-sm:sr-only">{{ t('library.downloadZip') }}</span>
        </UiButton>
        <UiButton
          v-if="!trash.enabled.value || auth.isAdmin.value"
          size="sm"
          variant="danger"
          icon="trash"
          @click="$emit('delete')"
        >
          <span class="max-sm:sr-only">{{
            trash.enabled.value ? t('trash.move') : t('actions.delete')
          }}</span>
        </UiButton>
        <UiIconButton
          icon="x"
          :label="t('library.clearSelection')"
          size="sm"
          @click="$emit('clear')"
        />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import UiButton from '../ui/UiButton.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useAuth } from '/src/model/auth'
import { useTrashCapability } from '/src/lib/trash'
import { useI18n } from '/src/i18n'

defineProps({
  count: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  zipping: { type: Boolean, default: false },
})
defineEmits([
  'select-all',
  'play',
  'enqueue',
  'zip',
  'delete',
  'clear',
  'add-to-playlist',
])
const { t } = useI18n()
const auth = useAuth()
// With the music trash on, only admins remove songs, and to the trash.
const trash = useTrashCapability()
</script>
