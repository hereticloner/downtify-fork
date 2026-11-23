<template>
  <!-- Tab strip: square cells separated by 1px rules, the active cell
       inverts. No underline, no movement. -->
  <div class="border-b-2 border-line">
    <div
      role="tablist"
      class="stagger-fade flex overflow-x-auto overflow-y-hidden [scrollbar-width:none]"
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
            : 'hover:bg-surface-2 hover:text-fg'
        "
        @click="$emit('update:modelValue', item.id)"
      >
        <span
          class="eyebrow"
          :class="
            item.id === modelValue
              ? 'text-on-invert'
              : 'text-muted group-hover:text-fg'
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
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import UiBadge from './UiBadge.vue'

defineProps({
  items: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
