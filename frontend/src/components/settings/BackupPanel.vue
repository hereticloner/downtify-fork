<template>
  <SettingGroup
    :title="t('settings.backupsTitle')"
    :description="t('settings.backupsHint')"
  >
    <div
      class="border-b-2 border-line-2 bg-surface-2 px-4 py-3 text-[12px] leading-relaxed text-muted"
    >
      {{ t('settings.backupSecretWarning') }}
    </div>
    <SettingRow
      :label="t('settings.backupSchedule')"
      :description="t('settings.backupScheduleHint')"
    >
      <UiSelect
        :model-value="schedule"
        :options="scheduleOptions"
        @update:model-value="saveSchedule"
      />
    </SettingRow>
    <SettingRow
      :label="t('settings.backupCreate')"
      :description="t('settings.backupCreateHint')"
    >
      <UiButton variant="secondary" :disabled="busy" @click="createBackup">
        {{ t('settings.backupCreate') }}
      </UiButton>
    </SettingRow>
    <div class="px-4 py-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h4 class="eyebrow text-fg">{{ t('settings.backupCopies') }}</h4>
        <label
          class="flex min-h-11 cursor-pointer items-center gap-3 text-sm text-fg"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".json.gz,application/gzip"
            class="sr-only"
            @change="uploadBackup"
          />
          <UiButton variant="secondary" :disabled="busy" @click="chooseFile">
            {{ t('settings.backupUpload') }}
          </UiButton>
        </label>
      </div>
      <p
        v-if="status"
        role="status"
        class="mt-2 text-[12px]"
        :class="statusError ? 'text-danger' : 'text-muted'"
      >
        {{ status }}
      </p>
      <ul class="mt-3 divide-y divide-line-2 border-2 border-line-2">
        <li v-if="!items.length" class="px-4 py-6 text-sm text-muted">
          {{ t('settings.backupEmpty') }}
        </li>
        <li
          v-for="item in items"
          :key="item.name"
          class="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
        >
          <div class="min-w-0">
            <p class="mono truncate text-[12px] text-fg">{{ item.name }}</p>
            <p class="mt-0.5 text-[11px] text-muted">
              {{ formatBackupDate(item.created_at) }} ·
              {{ formatBackupSize(item.size) }}
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <UiButton
              variant="secondary"
              :disabled="busy"
              @click="download(item.name)"
            >
              {{ t('settings.backupDownload') }}
            </UiButton>
            <UiButton
              variant="secondary"
              :disabled="busy"
              @click="preview(item.name)"
            >
              {{ t('settings.backupPreview') }}
            </UiButton>
            <UiButton
              variant="secondary"
              :disabled="busy"
              @click="remove(item.name)"
            >
              {{ t('settings.backupDelete') }}
            </UiButton>
          </div>
        </li>
      </ul>
    </div>
  </SettingGroup>

  <UiModal
    :open="Boolean(previewData)"
    :title="t('settings.backupPreviewTitle')"
    @close="previewData = null"
  >
    <p class="text-sm text-muted">{{ t('settings.backupPreviewBody') }}</p>
    <dl
      class="mt-4 grid grid-cols-2 gap-2 border-2 border-line-2 p-3 text-[12px]"
    >
      <template v-for="[key, value] in previewCounts" :key="key">
        <dt class="text-muted">{{ key }}</dt>
        <dd class="mono text-right text-fg">{{ value }}</dd>
      </template>
    </dl>
    <p
      v-if="previewData?.unresolved?.length"
      class="mt-3 text-[12px] text-danger"
    >
      {{
        t('settings.backupUnresolved', { count: previewData.unresolved.length })
      }}
    </p>
    <label
      class="mt-4 flex min-h-11 cursor-pointer items-center gap-3 text-sm text-fg"
    >
      <input
        v-model="requeueMissing"
        type="checkbox"
        class="size-4 accent-accent"
      />
      {{ t('settings.backupRequeue') }}
    </label>
    <div class="mt-5 flex justify-end gap-2">
      <UiButton variant="secondary" @click="previewData = null">
        {{ t('common.cancel') }}
      </UiButton>
      <UiButton :disabled="busy || !canRestore" @click="restore">
        {{ t('settings.backupRestore') }}
      </UiButton>
    </div>
  </UiModal>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import { useUi } from '/src/model/ui'
import {
  backupRestoreRequest,
  canRestoreBackup,
  formatBackupDate,
  formatBackupSize,
} from '/src/lib/backupSettings'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiModal from '/src/components/ui/UiModal.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'

const { t } = useI18n()
const ui = useUi()
const items = ref([])
const busy = ref(false)
const status = ref('')
const statusError = ref(false)
const previewData = ref(null)
const requeueMissing = ref(true)
const schedule = ref('off')
const fileInput = ref(null)
const scheduleOptions = computed(() => [
  { value: 'off', label: t('settings.backupScheduleOff') },
  { value: 'daily', label: t('settings.backupScheduleDaily') },
  { value: 'three_days', label: t('settings.backupScheduleThreeDays') },
  { value: 'weekly', label: t('settings.backupScheduleWeekly') },
])
const canRestore = computed(() => canRestoreBackup(previewData.value))
const previewCounts = computed(() =>
  Object.entries(previewData.value?.added || {})
)

async function load() {
  try {
    const res = await API.listBackups()
    items.value = res.data?.items || []
    schedule.value = res.data?.schedule || 'off'
  } catch {
    statusError.value = true
    status.value = t('settings.backupLoadFailed')
  }
}

async function createBackup() {
  busy.value = true
  status.value = ''
  try {
    await API.createBackup()
    await load()
    ui.toast(t('settings.backupCreated'), { kind: 'success' })
  } catch {
    statusError.value = true
    status.value = t('settings.backupFailed')
  } finally {
    busy.value = false
  }
}

function download(name) {
  window.location.href = `/api/backups/${encodeURIComponent(name)}`
}

async function preview(name) {
  busy.value = true
  status.value = ''
  try {
    const res = await API.previewBackup(
      backupRestoreRequest(name, true, requeueMissing.value)
    )
    previewData.value = { ...res.data, name }
  } catch {
    statusError.value = true
    status.value = t('settings.backupFailed')
  } finally {
    busy.value = false
  }
}

async function restore() {
  if (!previewData.value || !canRestore.value) return
  busy.value = true
  try {
    await API.restoreBackup(
      backupRestoreRequest(previewData.value.name, false, requeueMissing.value)
    )
    previewData.value = null
    await load()
    ui.toast(t('settings.backupRestored'), { kind: 'success' })
  } catch {
    statusError.value = true
    status.value = t('settings.backupFailed')
  } finally {
    busy.value = false
  }
}

async function remove(name) {
  const ok = await ui.confirm({
    title: t('settings.backupDeleteTitle'),
    body: t('settings.backupDeleteBody', { name }),
    confirmLabel: t('settings.backupDelete'),
    danger: true,
  })
  if (!ok) return
  busy.value = true
  try {
    await API.deleteBackup(name)
    await load()
  } catch {
    statusError.value = true
    status.value = t('settings.backupFailed')
  } finally {
    busy.value = false
  }
}

function chooseFile() {
  fileInput.value?.click()
}

async function uploadBackup(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  busy.value = true
  try {
    await API.uploadBackup(file)
    await load()
    ui.toast(t('settings.backupUploaded'), { kind: 'success' })
  } catch {
    statusError.value = true
    status.value = t('settings.backupFailed')
  } finally {
    busy.value = false
  }
}

async function saveSchedule(value) {
  schedule.value = value
  try {
    await API.setBackupSchedule(value)
  } catch {
    statusError.value = true
    status.value = t('settings.backupFailed')
  }
}

onMounted(load)
</script>
