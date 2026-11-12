<template>
  <div class="flex flex-wrap items-stretch gap-2">
    <!-- Presets are a block strip: one frame, 2px rules between. -->
    <div class="flex flex-wrap items-stretch border-2 border-line">
      <button
        v-for="preset in presets"
        :key="preset"
        type="button"
        class="tabular h-10 min-w-11 border-l-2 border-line px-3 text-[12px] font-semibold transition-colors duration-100 first:border-l-0"
        :class="
          preset === modelValue
            ? 'bg-invert text-on-invert'
            : 'text-fg-3 hover:bg-surface-2 hover:text-fg'
        "
        :aria-pressed="preset === modelValue"
        @click="$emit('update:modelValue', preset)"
      >
        {{ format ? format(preset) : preset }}
      </button>
    </div>
    <label
      class="flex h-10 items-center gap-1.5 border-2 border-line-2 px-2.5 transition-colors duration-100 focus-within:border-accent"
      :title="customLabel"
    >
      <span class="sr-only">{{ customLabel }}</span>
      <input
        type="number"
        inputmode="numeric"
        :min="min"
        :max="max"
        :value="modelValue"
        class="mono tabular w-14 bg-transparent text-fg outline-none"
        @change="onChange"
      />
      <span v-if="unit" class="mono shrink-0 text-faint">{{ unit }}</span>
    </label>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Number, default: 0 },
  presets: { type: Array, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  unit: { type: String, default: '' },
  customLabel: { type: String, default: '' },
  format: { type: Function, default: null },
})
const emit = defineEmits(['update:modelValue'])

function onChange(event) {
  const value = Number.parseInt(event.target.value, 10)
  const clamped = Number.isNaN(value)
    ? props.min
    : Math.min(props.max, Math.max(props.min, value))
  event.target.value = clamped
  emit('update:modelValue', clamped)
}
</script>
