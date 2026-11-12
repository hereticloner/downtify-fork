<template>
  <details
    v-if="auth.isAdmin.value"
    class="border-2 border-line bg-surface"
    @toggle="load"
  >
    <summary
      class="eyebrow flex cursor-pointer items-center justify-between gap-3 px-4 py-3 text-fg"
    >
      {{ t('downloadPolicy.exclusions') }}
      <AppIcon name="chevron-down" :size="14" class="text-muted" />
    </summary>
    <div class="border-t border-line-2 px-4 py-3">
      <p v-if="error" role="alert" class="mono text-danger">{{ error }}</p>
      <p v-if="loaded && !items.length" class="text-[13px] text-muted">
        {{ t('downloadPolicy.empty') }}
      </p>
      <ul class="flex flex-col">
        <li
          v-for="item in items"
          :key="item.id"
          class="flex items-center justify-between gap-3 border-b border-line-2 py-2 last:border-b-0 last:pb-0"
        >
          <div class="min-w-0">
            <div class="truncate text-[13px] font-medium">
              {{ item.title }} · {{ item.artist }}
            </div>
            <div class="mono truncate text-faint">
              {{ t(`downloadPolicy.${item.reason}`) }}
            </div>
          </div>
          <UiButton
            size="sm"
            variant="secondary"
            :disabled="busy"
            @click="resume(item.id)"
            >{{ t('downloadPolicy.resume') }}</UiButton
          >
        </li>
      </ul>
    </div>
  </details>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useI18n } from '/src/i18n'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'

const auth = useAuth(),
  { t } = useI18n()
const items = ref([]),
  error = ref(''),
  loaded = ref(false),
  busy = ref(false)
async function load() {
  if (!auth.isAdmin.value) return
  try {
    items.value = (await API.downloadExclusions()).data.items
    error.value = ''
    loaded.value = true
  } catch {
    error.value = t('downloadPolicy.error')
  }
}
async function resume(id) {
  busy.value = true
  try {
    await API.resumeDownload(id)
    await load()
  } catch {
    error.value = t('downloadPolicy.error')
  } finally {
    busy.value = false
  }
}
onMounted(() =>
  window.addEventListener('downtify-download-policy-changed', load)
)
onUnmounted(() =>
  window.removeEventListener('downtify-download-policy-changed', load)
)
</script>
