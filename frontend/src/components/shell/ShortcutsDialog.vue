<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex items-center justify-center bg-invert/60 p-4"
        @click.self="$emit('update:open', false)"
      >
        <div
          role="dialog"
          aria-modal="true"
          class="max-h-[92dvh] w-full max-w-lg animate-rise overflow-y-auto border-2 border-line bg-surface"
        >
          <header class="flex items-stretch border-b-2 border-line">
            <div class="min-w-0 flex-1 bg-invert px-4 py-3">
              <h2 class="text-display text-base font-bold text-on-invert">
                {{ t('shortcuts.title') }}
              </h2>
            </div>
            <div class="flex shrink-0 items-center border-l-2 border-line px-1">
              <UiIconButton
                ref="closeButton"
                icon="x"
                :label="t('common.close')"
                @click="$emit('update:open', false)"
              />
            </div>
          </header>
          <ul class="grid gap-x-6 p-4 sm:grid-cols-2">
            <li
              v-for="item in shortcuts"
              :key="item.label"
              class="flex items-center justify-between gap-3 border-b border-line-2 py-2 text-[13px]"
            >
              <span class="min-w-0 truncate text-fg-3">{{
                t(item.label)
              }}</span>
              <span class="flex shrink-0 gap-1">
                <kbd
                  v-for="key in item.keys"
                  :key="key"
                  class="mono flex h-6 min-w-6 items-center justify-center border-2 border-line bg-surface-2 px-1.5 text-fg"
                  >{{ key }}</kbd
                >
              </span>
            </li>
          </ul>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { visibleShortcuts } from './shortcuts'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useI18n } from '/src/i18n'

const props = defineProps({ open: { type: Boolean, default: false } })
defineEmits(['update:open'])
const { t } = useI18n()
const { showLyrics } = usePlayerPrefs()
const closeButton = ref(null)
const shortcuts = computed(() => visibleShortcuts({ lyrics: showLyrics.value }))

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    await nextTick()
    closeButton.value?.$el?.focus()
  }
)
</script>
