<template>
  <UiModal
    :open="open"
    :title="t('nav.more')"
    width="sm:max-w-md"
    @close="$emit('close')"
  >
    <div class="flex flex-col">
      <a
        v-if="hasUpdate"
        :href="update.release_url"
        target="_blank"
        rel="noopener"
        class="mb-1 flex h-14 items-center gap-4 rounded-control px-2 text-[15px] font-semibold text-accent"
        @click="$emit('close')"
      >
        <span
          class="flex size-9 items-center justify-center rounded-[10px] bg-accent/12"
        >
          <AppIcon name="sparkle" :size="18" />
        </span>
        {{ t('nav.updateAvailable', { version: update.latest_version }) }}
        <AppIcon name="arrow-up-right" :size="16" class="ml-auto" />
      </a>
      <RouterLink
        v-for="link in links"
        :key="link.name"
        :to="{ name: link.name }"
        class="flex h-14 items-center gap-4 rounded-control px-2 text-[15px] font-medium"
        @click="$emit('close')"
      >
        <span
          class="flex size-9 items-center justify-center rounded-[10px] bg-surface-2 text-fg-3"
        >
          <AppIcon :name="link.icon" :size="18" />
        </span>
        {{ t(link.label) }}
        <AppIcon name="chevron-right" :size="18" class="ml-auto text-faint" />
      </RouterLink>
      <button
        type="button"
        class="flex h-14 w-full items-center gap-4 rounded-control px-2 text-[15px] font-medium"
        @click="theme.toggle()"
      >
        <span
          class="flex size-9 items-center justify-center rounded-[10px] bg-surface-2 text-fg-3"
        >
          <AppIcon
            :name="theme.resolved.value === 'dark' ? 'sun' : 'moon'"
            :size="18"
          />
        </span>
        {{
          theme.resolved.value === 'dark'
            ? t('settings.themeLight')
            : t('settings.themeDark')
        }}
      </button>
      <button
        v-if="auth.user.value && !auth.authDisabled.value"
        type="button"
        class="flex h-14 w-full items-center gap-4 rounded-control px-2 text-[15px] font-medium"
        @click="auth.signOut"
      >
        <span
          class="flex size-9 items-center justify-center rounded-[10px] bg-surface-2 text-fg-3"
        >
          <AppIcon name="log-out" :size="18" />
        </span>
        {{ t('nav.signOut') }}
        <span class="ml-auto truncate text-[13px] text-faint">{{
          auth.user.value.username
        }}</span>
      </button>
    </div>
  </UiModal>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiModal from '../ui/UiModal.vue'
import { useI18n } from '/src/i18n'
import { useAuth } from '/src/model/auth'
import { useTheme } from '/src/model/theme'
import { useUpdateCheck } from '/src/model/updateCheck'

defineProps({
  open: { type: Boolean, default: false },
  // [{ name, icon, label }] — the secondary destinations.
  links: { type: Array, required: true },
})
defineEmits(['close'])

const { t } = useI18n()
const theme = useTheme()
const auth = useAuth()
const update = useUpdateCheck().status
const hasUpdate = computed(() => Boolean(update.value?.update_available))
</script>
