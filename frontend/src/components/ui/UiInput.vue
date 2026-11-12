<template>
  <div class="flex min-w-0 flex-col gap-1.5">
    <label v-if="label" :for="inputId" class="eyebrow text-fg-3">{{
      label
    }}</label>
    <span
      class="flex h-11 items-center gap-2.5 border-2 bg-bg px-3 transition-colors duration-100"
      :class="[
        error ? 'border-danger' : 'border-line-2 focus-within:border-accent',
        readonly ? 'bg-surface-2 text-muted' : '',
      ]"
    >
      <AppIcon v-if="icon" :name="icon" :size="17" class="text-faint" />
      <input
        :id="inputId"
        :type="inputType"
        :value="modelValue"
        :placeholder="placeholder"
        :inputmode="inputmode"
        :min="min"
        :max="max"
        :autocomplete="autocomplete"
        :readonly="readonly"
        :aria-readonly="readonly ? 'true' : undefined"
        :spellcheck="false"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="error || hint ? noteId : undefined"
        :list="list || undefined"
        class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
        :class="[
          mono ? 'mono' : 'font-sans',
          readonly ? 'cursor-default text-muted' : 'text-fg',
        ]"
        @input="onInput"
        @change="$emit('change', $event.target.value)"
      />
      <span v-if="suffix" class="mono shrink-0 text-faint">{{ suffix }}</span>
      <button
        v-if="type === 'password' && !readonly"
        type="button"
        class="eyebrow shrink-0 text-muted transition-colors duration-100 hover:text-fg"
        @click="reveal = !reveal"
      >
        {{ reveal ? t('common.hide') : t('common.show') }}
      </button>
    </span>
    <span v-if="error" :id="noteId" class="text-[11px] text-danger">{{
      error
    }}</span>
    <span v-else-if="hint" :id="noteId" class="text-[11px] text-muted">{{
      hint
    }}</span>
  </div>
</template>

<script setup>
import { computed, ref, useId } from 'vue'
import AppIcon from './AppIcon.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  type: { type: String, default: 'text' },
  icon: { type: String, default: '' },
  suffix: { type: String, default: '' },
  mono: { type: Boolean, default: false },
  // Shown but not editable (e.g. a value set by the server's environment).
  readonly: { type: Boolean, default: false },
  min: { type: [String, Number], default: undefined },
  max: { type: [String, Number], default: undefined },
  inputmode: { type: String, default: undefined },
  autocomplete: { type: String, default: 'off' },
  list: { type: String, default: '' },
  modelModifiers: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue', 'change'])
const { t } = useI18n()
const reveal = ref(false)
const inputId = `input-${useId()}`
const noteId = `${inputId}-note`

const inputType = computed(() =>
  props.type === 'password' && reveal.value ? 'text' : props.type
)

function onInput(event) {
  let raw = event.target.value
  if (props.modelModifiers.trim) raw = raw.trim()
  emit(
    'update:modelValue',
    props.type === 'number' && raw !== '' ? Number(raw) : raw
  )
}
</script>
