<template>
  <div class="flex items-center gap-1">
    <input
      ref="fileInput"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="sr-only"
      @change="upload"
    />
    <UiIconButton
      icon="upload"
      :label="t('collections.coverUpload')"
      :disabled="busy"
      @click="choose"
    />
    <UiIconButton
      v-if="hasCover"
      icon="trash"
      :label="t('collections.coverRemove')"
      :disabled="busy"
      @click="remove"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from '/src/i18n'
import { useUi } from '/src/model/ui'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import {
  removeCollectionCover,
  uploadCollectionCover,
} from '/src/model/collections'

const props = defineProps({
  name: { type: String, required: true },
  hasCover: { type: Boolean, default: false },
})
const emit = defineEmits(['changed'])
const { t } = useI18n()
const ui = useUi()
const fileInput = ref(null)
const busy = ref(false)

function choose() {
  fileInput.value?.click()
}
async function upload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  busy.value = true
  try {
    await uploadCollectionCover(props.name, file)
    emit('changed')
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    busy.value = false
    event.target.value = ''
  }
}
async function remove() {
  busy.value = true
  try {
    await removeCollectionCover(props.name)
    emit('changed')
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    busy.value = false
  }
}
</script>
