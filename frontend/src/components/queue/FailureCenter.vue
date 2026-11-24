<template>
  <UiPanel
    v-if="items.length"
    :title="t('queue.failureCenterTitle')"
    :description="t('queue.failureCenterHint')"
  >
    <ul class="flex flex-col gap-3">
      <li
        v-for="row in items"
        :key="row.song_id"
        class="border-b-2 border-line-2 pb-3 last:border-b-0 last:pb-0"
      >
        <div class="flex items-start gap-3">
          <CoverArt
            :src="deezerImage(row.song.cover_url)"
            :name="row.song.album_name || row.song.name"
            :letter-size="10"
            :icon-size="12"
            class="size-9 shrink-0"
          />
          <div class="min-w-0 flex-1">
            <p class="truncate text-[13px] font-semibold">
              {{ row.song.name || row.song_id }}
            </p>
            <p class="mono mt-0.5 truncate text-muted">
              {{ row.song.artist || (row.song.artists || []).join(', ') }}
            </p>
            <p class="mt-1 line-clamp-2 text-[12px] text-danger">
              {{ row.message }}
            </p>
            <p class="mono mt-1 text-faint">
              {{
                t('queue.failureAttempts', {
                  count: row.attempts,
                })
              }}
            </p>
          </div>
        </div>
        <div v-if="auth.isAdmin.value" class="mt-2 flex flex-wrap gap-2">
          <UiButton
            size="sm"
            variant="secondary"
            icon="retry"
            :loading="busy === row.song_id"
            @click="retry(row)"
          >
            {{ t('queue.retry') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            icon="x"
            :disabled="busy === row.song_id"
            @click="exclude(row)"
          >
            {{ t('downloadPolicy.block') }}
          </UiButton>
        </div>
      </li>
    </ul>
    <UiButton
      v-if="auth.isAdmin.value"
      size="sm"
      variant="ghost"
      icon="trash"
      class="mt-3"
      @click="clear"
    >
      {{ t('queue.failureClear') }}
    </UiButton>
  </UiPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useDownloadFailures } from '/src/model/downloadFailures'
import { useUi } from '/src/model/ui'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import { deezerImage } from '/src/lib/deezerImage'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const auth = useAuth()
const ui = useUi()
const failures = useDownloadFailures()
const busy = ref('')
const items = computed(() => failures.items.value.slice(0, 20))

onMounted(failures.load)

async function retry(row) {
  busy.value = row.song_id
  try {
    await failures.retry(row.song_id)
    ui.toast(t('queue.failureRetryQueued'))
  } catch {
    ui.toast(t('queue.failureRetryFailed'), { kind: 'error' })
  } finally {
    busy.value = ''
  }
}

async function exclude(row) {
  const song = row.song || {}
  busy.value = row.song_id
  try {
    await API.excludeDownload({
      song_id: row.song_id,
      name: song.name || '',
      artist: song.artist || '',
      artists: Array.isArray(song.artists) ? song.artists : [],
      album_name: song.album_name || '',
      duration: Number(song.duration) || 0,
    })
    failures.dismiss(row.song_id)
    window.dispatchEvent(new Event('downtify-download-policy-changed'))
    ui.toast(t('downloadPolicy.blocked'))
  } catch {
    ui.toast(t('downloadPolicy.error'), { kind: 'error' })
  } finally {
    busy.value = ''
  }
}

async function clear() {
  if (
    !(await ui.confirm({
      title: t('queue.failureClear'),
      body: t('queue.failureCenterHint'),
      confirmLabel: t('queue.failureClear'),
    }))
  )
    return
  try {
    await failures.clear()
  } catch {
    ui.toast(t('queue.failureRetryFailed'), { kind: 'error' })
  }
}
</script>
