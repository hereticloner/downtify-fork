<template>
  <!-- Tab strip: square cells separated by 1px rules, the active cell
       inverts. One accent marker slides beneath the active tab. -->
  <div class="border-b-2 border-line">
    <div
      ref="listRef"
      role="tablist"
      class="stagger-fade relative flex overflow-x-auto overflow-y-hidden [scrollbar-width:none]"
    >
      <component
        :is="item.to ? RouterLink : 'button'"
        v-for="item in items"
        :key="item.id"
        :to="item.to || undefined"
        :type="item.to ? undefined : 'button'"
        role="tab"
        :aria-selected="item.id === modelValue"
        class="group flex shrink-0 items-center gap-2 border-l border-line-2 px-4 py-2.5 whitespace-nowrap transition-colors duration-100 first:border-l-0"
        :class="
          item.id === modelValue
            ? 'bg-invert'
            : 'hover:bg-surface-2 hover:text-accent'
        "
        @click="$emit('update:modelValue', item.id)"
      >
        <span
          class="eyebrow"
          :class="
            item.id === modelValue
              ? 'text-on-invert'
              : 'text-muted group-hover:text-accent'
          "
          >{{ item.label }}</span
        >
        <UiBadge
          v-if="item.count !== undefined && item.count !== null"
          :tone="item.id === modelValue ? 'accent' : 'neutral'"
        >
          {{ item.count }}
        </UiBadge>
      </component>
      <span
        class="tab-indicator pointer-events-none absolute bottom-0 left-0 h-0.5 bg-accent"
        :style="{
          transform: `translateX(${indicator.x}px)`,
          width: `${indicator.w}px`,
        }"
        aria-hidden="true"
      />
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import UiBadge from './UiBadge.vue'

const props = defineProps({
  items: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

// A4: one marker for the whole strip. Measuring the active tab keeps it
// aligned as selection changes; the slide itself is a CSS transition.
const listRef = ref(null)
const indicator = ref({ x: 0, w: 0 })
function measureIndicator() {
  const active = listRef.value?.querySelector('[aria-selected="true"]')
  if (!active) return
  indicator.value = { x: active.offsetLeft, w: active.offsetWidth }
}
onMounted(measureIndicator)
watch(() => props.modelValue, () => nextTick(measureIndicator))
</script>
