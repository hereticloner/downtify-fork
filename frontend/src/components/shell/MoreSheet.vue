<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex bg-bg"
        @keydown="onKeydown"
      >
        <div
          ref="panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          class="flex h-dvh w-full flex-col bg-bg outline-none"
        >
          <header
            class="flex h-11 shrink-0 items-stretch border-b-2 border-line bg-invert text-on-invert"
          >
            <div class="flex min-w-0 flex-1 items-center gap-2.5 px-3">
              <span
                class="flex size-7 shrink-0 items-center justify-center bg-bg"
              >
                <AppLogo :size="18" />
              </span>
              <h2
                :id="titleId"
                class="text-display truncate text-[15px] font-bold text-on-invert"
              >
                {{ t('nav.more') }}
              </h2>
              <span
                class="eyebrow ml-auto shrink-0 border border-on-invert/40 px-1.5 py-0.5 text-on-invert"
                >{{ links.length }}</span
              >
            </div>
            <div
              class="flex shrink-0 items-center border-l-2 border-line bg-bg"
            >
              <UiIconButton
                icon="x"
                :label="t('common.close')"
                size="sm"
                class="m-1"
                @click="$emit('close')"
              />
            </div>
          </header>

          <div class="min-h-0 flex-1 overflow-y-auto">
            <a
              v-if="hasUpdate"
              :href="update.release_url"
              target="_blank"
              rel="noopener"
              class="flex h-[60px] items-center gap-3 border-b-2 border-line px-3 transition-colors duration-100 hover:bg-surface-2"
              @click="$emit('close')"
            >
              <span
                class="flex size-8 shrink-0 items-center justify-center border-2 border-line"
              >
                <AppIcon name="sparkle" :size="16" />
              </span>
              <span class="eyebrow min-w-0 flex-1 truncate text-fg">{{
                t('nav.updateAvailable', { version: update.latest_version })
              }}</span>
              <AppIcon name="arrow-up-right" :size="16" class="text-faint" />
            </a>

            <RouterLink
              v-for="link in links"
              :key="link.name"
              :to="{ name: link.name }"
              class="flex h-[60px] items-center gap-3 border-b-2 border-line px-3 transition-colors duration-100"
              :class="
                link.active
                  ? 'bg-invert text-on-invert hover:bg-invert'
                  : 'text-fg hover:bg-surface-2'
              "
              :aria-current="link.active ? 'page' : undefined"
              @click="$emit('close')"
            >
              <span
                class="flex size-8 shrink-0 items-center justify-center border-2"
                :class="link.active ? 'border-on-invert' : 'border-line-2'"
              >
                <AppIcon :name="link.icon" :size="16" />
              </span>
              <span class="min-w-0 flex-1 truncate text-[15px] font-medium">{{
                t(link.label)
              }}</span>
              <span
                v-if="link.count"
                class="mono flex h-[18px] min-w-[18px] items-center justify-center px-1"
                :class="
                  link.active ? 'bg-bg text-fg' : 'bg-invert text-on-invert'
                "
                >{{ link.count }}</span
              >
              <AppIcon
                name="chevron-right"
                :size="16"
                :class="link.active ? 'text-on-invert' : 'text-faint'"
              />
            </RouterLink>

            <button
              type="button"
              class="flex h-[60px] w-full items-center gap-3 border-b-2 border-line px-3 text-left transition-colors duration-100 hover:bg-surface-2"
              @click="theme.toggle()"
            >
              <span
                class="flex size-8 shrink-0 items-center justify-center border-2 border-line-2"
              >
                <AppIcon
                  :name="theme.resolved.value === 'dark' ? 'sun' : 'moon'"
                  :size="16"
                />
              </span>
              <span class="min-w-0 flex-1 truncate text-[15px] font-medium">
                {{
                  theme.resolved.value === 'dark'
                    ? t('settings.themeLight')
                    : t('settings.themeDark')
                }}
              </span>
            </button>

            <button
              v-if="auth.user.value && !auth.authDisabled.value"
              type="button"
              class="flex h-[60px] w-full items-center gap-3 border-b-2 border-line px-3 text-left transition-colors duration-100 hover:bg-surface-2"
              @click="auth.signOut"
            >
              <span
                class="flex size-8 shrink-0 items-center justify-center border-2 border-line-2"
              >
                <AppIcon name="log-out" :size="16" />
              </span>
              <span class="min-w-0 flex-1 truncate text-[15px] font-medium">{{
                t('nav.signOut')
              }}</span>
              <span class="mono max-w-[14ch] truncate text-faint">{{
                auth.user.value.username
              }}</span>
            </button>
          </div>

          <footer
            class="flex shrink-0 items-center justify-between border-t-2 border-line px-3 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
          >
            <span class="mono truncate text-faint">{{
              auth.user.value?.username || ''
            }}</span>
            <span v-if="version" class="mono shrink-0 text-faint"
              >Downtify {{ version }}</span
            >
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, useId } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import AppLogo from '../ui/AppLogo.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useAuth } from '/src/model/auth'
import { useDialogFocus } from '/src/model/dialogFocus'
import { useTheme } from '/src/model/theme'
import { useUpdateCheck } from '/src/model/updateCheck'
import { useI18n } from '/src/i18n'

const props = defineProps({
  open: { type: Boolean, default: false },
  // [{ name, icon, label, active?, count? }] — every destination.
  links: { type: Array, required: true },
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const theme = useTheme()
const auth = useAuth()
const update = useUpdateCheck().status
const hasUpdate = computed(() => Boolean(update.value?.update_available))
const panel = ref(null)
const titleId = `modal-${useId()}`
const version = computed(() => {
  const v = localStorage.getItem('version')
  return v && v !== '0.0.0' ? v : ''
})

// Full-height panel, same dialog contract as every other sheet: Escape
// closes, Tab stays inside, focus returns to the menu button on close.
const { onKeydown } = useDialogFocus({
  open: () => props.open,
  panel,
  onClose: () => emit('close'),
})
</script>
