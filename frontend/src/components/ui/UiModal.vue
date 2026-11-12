<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex items-end justify-center bg-black/60 sm:items-center sm:p-4"
        @pointerdown.self="pressedBackdrop = true"
        @click.self="onBackdrop"
      >
        <div
          ref="panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          class="flex max-h-[92dvh] w-full animate-rise flex-col overflow-hidden border-2 border-line bg-surface outline-none"
          :class="width"
          @keydown="onKeydown"
        >
          <header class="flex shrink-0 items-stretch border-b-2 border-line">
            <div
              class="min-w-0 flex-1 bg-invert px-5 py-4 text-on-invert sm:px-6"
            >
              <h2
                :id="titleId"
                class="text-display text-lg font-bold text-on-invert"
              >
                {{ title }}
              </h2>
              <p v-if="description" class="mt-1 text-[13px] text-on-invert/70">
                {{ description }}
              </p>
            </div>
            <div
              class="flex shrink-0 items-center border-l-2 border-line bg-surface px-2"
            >
              <UiIconButton
                icon="x"
                :label="t('common.close')"
                @click="$emit('close')"
              />
            </div>
          </header>
          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
            <slot />
          </div>
          <footer
            v-if="$slots.footer"
            class="flex shrink-0 flex-col-reverse gap-2 border-t-2 border-line px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:flex-row sm:justify-end sm:px-6"
          >
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, useId } from 'vue'
import UiIconButton from './UiIconButton.vue'
import { useDialogFocus } from '/src/model/dialogFocus'
import { useI18n } from '/src/i18n'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  width: { type: String, default: 'sm:max-w-lg' },
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const titleId = `modal-${useId()}`
const panel = ref(null)
// Only a click that also started on the backdrop closes the dialog, so
// selecting text in a field and releasing outside doesn't.
const pressedBackdrop = ref(false)

function initialFocus(panelEl, items) {
  // On touch screens focus the dialog itself, so the keyboard doesn't
  // pop up; otherwise the first field, else the first button after the
  // close button.
  const touch = window.matchMedia?.('(pointer: coarse)').matches
  if (touch) return panelEl
  return (
    panelEl?.querySelector('input, select, textarea') || items[1] || items[0]
  )
}

const { onKeydown } = useDialogFocus({
  open: () => props.open,
  panel,
  onClose: () => emit('close'),
  initialFocus,
})

function onBackdrop() {
  if (pressedBackdrop.value) emit('close')
  pressedBackdrop.value = false
}
</script>
