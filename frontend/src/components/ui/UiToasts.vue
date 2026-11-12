<template>
  <!-- Above UiModal (z-[80]) and UiDialog (z-[90]): saving from inside a
       modal toasts its result, which has to be seen on top of it. -->
  <div
    class="pointer-events-none fixed inset-x-0 bottom-[calc(env(safe-area-inset-bottom)+9.5rem)] z-[100] flex flex-col items-center gap-2 px-4 lg:bottom-28"
    aria-live="polite"
  >
    <TransitionGroup name="fade">
      <div
        v-for="item in toasts"
        :key="item.id"
        class="pointer-events-auto flex max-w-md items-center gap-3 border-y-2 border-r-2 border-l-4 border-line border-l-accent bg-surface py-2.5 pr-2 pl-3 text-sm text-fg"
      >
        <AppIcon
          :name="icons[item.kind] || 'info'"
          :size="18"
          :class="colors[item.kind] || 'text-muted'"
        />
        <span class="min-w-0 flex-1 text-pretty">{{ item.text }}</span>
        <button
          v-if="item.action"
          type="button"
          class="border border-line px-2 py-1 text-[11px] font-semibold tracking-[0.06em] uppercase transition-colors duration-100 hover:bg-surface-2"
          @click="runAction(item)"
        >
          {{ item.action.label }}
        </button>
        <UiIconButton
          icon="x"
          :label="t('common.close')"
          size="sm"
          @click="dismiss(item.id)"
        />
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import AppIcon from './AppIcon.vue'
import UiIconButton from './UiIconButton.vue'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const { toasts, dismiss } = useUi()
const { t } = useI18n()
const icons = { success: 'check-circle', error: 'alert', info: 'info' }
const colors = {
  success: 'text-accent',
  error: 'text-danger',
  info: 'text-muted',
}

function runAction(item) {
  dismiss(item.id)
  item.action.run()
}
</script>
