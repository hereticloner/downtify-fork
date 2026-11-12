<template>
  <UiIconButton
    :icon="liked ? 'heart' : 'heart-outline'"
    :label="liked ? t('likes.unlike') : t('likes.like')"
    :size="size"
    :active="liked"
    toggle
    :disabled="!file"
    @click.stop="likes.toggle(file)"
  />
</template>

<script setup>
import { computed } from 'vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useLikes } from '/src/model/likes'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // The track's library path, as `GET /tracks` reports it.
  file: { type: String, default: '' },
  size: { type: String, default: 'sm' },
})

const { t } = useI18n()
const likes = useLikes()
// The inverted block the primitive gives a selected toggle is the whole
// feedback; no scale pop, no colour pulse.
const liked = computed(() => likes.isLiked(props.file))
</script>
