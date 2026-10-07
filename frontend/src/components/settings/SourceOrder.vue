<template>
  <ProviderOrder
    :model-value="modelValue"
    :providers="providers"
    @update:model-value="(value) => $emit('update:modelValue', value)"
  >
    <template #badge="{ row }">
      <SourceBadge :source="row.id" />
    </template>
  </ProviderOrder>
</template>

<script setup>
import { computed } from 'vue'
import ProviderOrder from './ProviderOrder.vue'
import SourceBadge from '../ui/SourceBadge.vue'
import { useI18n } from '/src/i18n'

defineProps({ modelValue: { type: Array, required: true } })
defineEmits(['update:modelValue'])
const { t } = useI18n()

const providers = computed(() => [
  {
    id: 'youtube-music',
    title: t('settings.sourceYtm'),
    description: t('settings.sourceYtmHint'),
  },
  {
    id: 'youtube',
    title: t('settings.sourceYt'),
    description: t('settings.sourceYtHint'),
  },
])
</script>
