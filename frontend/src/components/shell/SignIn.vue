<template>
  <main
    class="flex min-h-dvh flex-col items-center justify-center bg-bg px-4 py-10 text-fg"
  >
    <div class="w-full max-w-[520px] border-2 border-line bg-surface">
      <header
        class="flex items-start gap-3 border-b-2 border-line bg-invert px-5 py-4 text-on-invert"
      >
        <span
          class="flex size-10 shrink-0 items-center justify-center bg-bg sm:size-11"
        >
          <AppLogo :size="30" />
        </span>
        <div class="min-w-0 flex-1">
          <h1 class="text-display text-xl font-bold text-on-invert">
            {{ t('auth.signInTitle') }}
          </h1>
          <p class="mt-1 text-[13px] text-on-invert/70">
            {{ t('auth.signInBody') }}
          </p>
        </div>
        <span
          v-if="version"
          class="mono hidden shrink-0 border border-on-invert/40 px-1.5 py-0.5 text-on-invert sm:flex"
          >{{ version }}</span
        >
      </header>

      <form class="flex flex-col gap-4 p-5 sm:p-6" @submit.prevent="submit">
        <UiInput
          v-model="username"
          :label="t('auth.username')"
          icon="user"
          autocomplete="username"
        />
        <UiInput
          v-model="password"
          type="password"
          :label="t('auth.password')"
          icon="lock"
          autocomplete="current-password"
          :error="error"
        />
        <UiButton
          type="submit"
          variant="primary"
          size="lg"
          class="w-full"
          :loading="busy"
          :disabled="!username.trim() || !password"
        >
          {{ t('auth.signIn') }}
        </UiButton>
        <p class="text-center text-[12px] text-faint">
          {{ t('auth.forgotHint') }}
        </p>
      </form>

      <footer
        class="flex items-center justify-between gap-3 border-t-2 border-line px-5 py-2"
      >
        <span class="mono truncate text-faint">{{ server }}</span>
        <span class="mono shrink-0 text-faint">Downtify {{ version }}</span>
      </footer>
    </div>

    <!-- A server upgraded from a version without accounts says so once. -->
    <UiModal
      :open="noticeOpen"
      :title="t('auth.noticeTitle')"
      @close="noticeOpen = false"
    >
      <div class="flex flex-col gap-4 text-sm text-pretty text-fg-2">
        <p>{{ t('auth.noticeBody') }}</p>
        <dl
          v-if="notice"
          class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 border-2 border-line-2 bg-surface-2 px-4 py-3"
        >
          <dt class="text-muted">{{ t('auth.username') }}</dt>
          <dd class="mono font-semibold select-all">
            {{ notice.username }}
          </dd>
          <dt class="text-muted">{{ t('auth.password') }}</dt>
          <dd
            class="font-semibold"
            :class="notice.password ? 'mono select-all' : ''"
          >
            {{ notice.password || t('auth.noticeKeptPassword') }}
          </dd>
        </dl>
        <p class="text-muted">{{ t('auth.noticeChange') }}</p>
      </div>
      <template #footer>
        <UiButton variant="primary" @click="useNotice">
          {{ t('auth.noticeOk') }}
        </UiButton>
      </template>
    </UiModal>
  </main>
</template>

<script setup>
// Shown instead of the app while this browser isn't signed in (see
// model/auth.js).
import { computed, ref, watch } from 'vue'
import AppLogo from '../ui/AppLogo.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import { useAuth } from '/src/model/auth'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const auth = useAuth()
const username = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

const version = computed(() => {
  const v = localStorage.getItem('version')
  return v && v !== '0.0.0' ? v : ''
})
const server = typeof window === 'undefined' ? '' : window.location.host

const notice = computed(() => auth.status.value?.notice || null)
const noticeOpen = ref(false)
watch(
  notice,
  (value) => {
    if (value) noticeOpen.value = true
  },
  { immediate: true }
)

function useNotice() {
  username.value = notice.value?.username || username.value
  if (notice.value?.password) password.value = notice.value.password
  noticeOpen.value = false
}

async function submit() {
  if (!username.value.trim() || !password.value || busy.value) return
  busy.value = true
  error.value = ''
  const result = await auth.signIn(username.value.trim(), password.value)
  if (result !== true) {
    if (result === 'wrongPassword') error.value = t('auth.wrongPassword')
    else if (result === 'tooMany') error.value = t('auth.tooMany')
    else error.value = String(result)
    busy.value = false
  }
}
</script>
