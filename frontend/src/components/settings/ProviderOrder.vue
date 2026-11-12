<template>
  <!-- Provider table: priority block, source chip, name + description, and
       the ON/OFF square at the end of the row. -->
  <ol class="flex min-w-0 flex-col" :class="dense ? '' : 'p-3'">
    <li
      v-for="(row, i) in rows"
      :key="row.id"
      class="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-line-2 px-2 py-2.5 transition-colors duration-100 last:border-b-0"
      :class="[
        row.enabled ? '' : 'opacity-50',
        dragOver === i
          ? 'outline outline-2 -outline-offset-2 outline-accent'
          : '',
      ]"
      :draggable="row.enabled"
      @dragstart="dragFrom = i"
      @dragover.prevent="dragOver = i"
      @dragleave="dragOver = -1"
      @drop.prevent="drop(i)"
      @dragend="dragOver = -1"
    >
      <AppIcon
        name="grip"
        :size="16"
        class="hidden cursor-grab text-faint sm:block"
      />
      <span
        class="mono flex size-6 shrink-0 items-center justify-center border tabular"
        :class="
          row.enabled
            ? 'border-line bg-invert text-on-invert'
            : 'border-line-2 text-faint'
        "
        >{{ row.enabled ? position(row.position) : '–' }}</span
      >
      <slot name="badge" :row="row" />
      <div class="min-w-0 flex-1 basis-40">
        <p class="truncate text-[13px] font-semibold">{{ row.title }}</p>
        <p class="text-[12px] text-pretty text-muted">{{ row.description }}</p>
      </div>
      <div class="ml-auto flex shrink-0 items-center gap-1">
        <UiIconButton
          icon="chevron-up"
          :label="t('settings.moveUp')"
          size="sm"
          :disabled="!row.enabled || row.position === 1"
          @click="apply(moveProvider(enabled, row.id, -1))"
        />
        <UiIconButton
          icon="chevron-down"
          :label="t('settings.moveDown')"
          size="sm"
          :disabled="!row.enabled || row.position === enabled.length"
          @click="apply(moveProvider(enabled, row.id, 1))"
        />
      </div>
      <UiSwitch
        :model-value="row.enabled"
        :aria-label="row.title"
        @update:model-value="(on) => toggle(row.id, on)"
      />
    </li>
  </ol>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import {
  dropProvider,
  moveProvider,
  providerRows,
  toggleProvider,
} from '/src/lib/providerOrder'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // Enabled provider ids, in the order they're tried.
  modelValue: { type: Array, required: true },
  // Every provider: [{ id, title, description }]
  providers: { type: Array, required: true },
  // Ids that belong at the top of the list when switched on.
  firstWhenEnabled: { type: Array, default: () => [] },
  // No padding of its own: for use inside a setting row.
  dense: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'enabled'])
const { t } = useI18n()
const dragOver = ref(-1)
const dragFrom = ref(-1)

const all = computed(() => props.providers.map((provider) => provider.id))
const info = computed(() =>
  Object.fromEntries(props.providers.map((provider) => [provider.id, provider]))
)
const enabled = computed(() =>
  props.modelValue.filter((id) => all.value.includes(id))
)
const rows = computed(() => providerRows(all.value, enabled.value, info.value))

// Priority is a technical value: two digits, monospaced.
function position(value) {
  return String(value).padStart(2, '0')
}

function apply(next) {
  if (next) emit('update:modelValue', next)
}

function toggle(id, on) {
  apply(
    toggleProvider(enabled.value, id, on, {
      first: props.firstWhenEnabled.includes(id),
    })
  )
  if (on) emit('enabled', id)
}

function drop(index) {
  const from = rows.value[dragFrom.value]
  const to = rows.value[index]
  dragOver.value = -1
  if (!from?.enabled || !to?.enabled) return
  apply(dropProvider(enabled.value, from.id, to.id))
}
</script>
