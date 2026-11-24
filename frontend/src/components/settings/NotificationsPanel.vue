<template>
  <SettingGroup
    :title="t('settings.notificationsTitle')"
    :description="t('settings.notificationsHint')"
  >
    <SettingRow
      :label="t('settings.notificationsEnabled')"
      :description="t('settings.notificationsEnabledHint')"
    >
      <UiSwitch
        v-model="config.enabled"
        :aria-label="t('settings.notificationsEnabled')"
      />
    </SettingRow>

    <template v-if="config.enabled">
      <SettingRow
        v-for="channel in channels"
        :key="channel.name"
        :label="t(channel.labelKey)"
        :description="t(channel.hintKey)"
      >
        <UiSwitch
          v-model="config.channels[channel.name].enabled"
          :aria-label="t(channel.labelKey)"
        />
      </SettingRow>

      <template v-if="config.channels.telegram.enabled">
        <div class="grid gap-4 px-4 py-4 sm:grid-cols-2">
          <UiInput
            v-model="config.channels.telegram.bot_token"
            :label="t('settings.telegramBotToken')"
            :placeholder="savedHint('telegram', 'bot_token_set')"
            type="password"
            autocomplete="new-password"
          />
          <UiInput
            v-model.trim="config.channels.telegram.chat_id"
            :label="t('settings.telegramChatId')"
            :hint="t('settings.telegramChatIdHint')"
            :placeholder="savedHint('telegram', 'chat_id_set')"
            inputmode="numeric"
            autocomplete="off"
          />
        </div>
        <div class="flex flex-wrap items-center gap-3 px-4 py-4">
          <UiButton
            variant="secondary"
            :disabled="testing === 'telegram'"
            @click="testChannel('telegram')"
          >
            {{ t('settings.testNotification') }}
          </UiButton>
          <span
            v-if="results.telegram === 'sent'"
            role="status"
            class="text-[13px] text-accent"
          >
            {{ t('settings.notificationSent') }}
          </span>
          <span
            v-else-if="results.telegram === 'failed'"
            role="status"
            class="text-[13px] text-danger"
          >
            {{ t('settings.notificationFailed') }}
          </span>
        </div>
      </template>

      <template v-if="config.channels.ntfy.enabled">
        <div class="grid gap-4 px-4 py-4 sm:grid-cols-2">
          <UiInput
            v-model="config.channels.ntfy.url"
            :label="t('settings.ntfyUrl')"
            :hint="t('settings.ntfyUrlHint')"
            :placeholder="savedHint('ntfy', 'url_set')"
            type="password"
            autocomplete="new-password"
          />
          <UiInput
            v-model="config.channels.ntfy.token"
            :label="t('settings.ntfyToken')"
            :hint="t('settings.ntfyTokenHint')"
            :placeholder="savedHint('ntfy', 'token_set')"
            type="password"
            autocomplete="new-password"
          />
        </div>
        <div class="flex flex-wrap items-center gap-3 px-4 py-4">
          <UiButton
            variant="secondary"
            :disabled="testing === 'ntfy'"
            @click="testChannel('ntfy')"
          >
            {{ t('settings.testNotification') }}
          </UiButton>
          <span
            v-if="results.ntfy === 'sent'"
            role="status"
            class="text-[13px] text-accent"
          >
            {{ t('settings.notificationSent') }}
          </span>
          <span
            v-else-if="results.ntfy === 'failed'"
            role="status"
            class="text-[13px] text-danger"
          >
            {{ t('settings.notificationFailed') }}
          </span>
        </div>
      </template>

      <template v-if="config.channels.webhook.enabled">
        <div class="grid gap-4 px-4 py-4 sm:grid-cols-2">
          <UiInput
            v-model="config.channels.webhook.url"
            :label="t('settings.webhookUrl')"
            :hint="t('settings.webhookUrlHint')"
            :placeholder="savedHint('webhook', 'url_set')"
            type="password"
            autocomplete="new-password"
          />
          <UiInput
            v-model="config.channels.webhook.token"
            :label="t('settings.webhookToken')"
            :hint="t('settings.webhookTokenHint')"
            :placeholder="savedHint('webhook', 'token_set')"
            type="password"
            autocomplete="new-password"
          />
        </div>
        <div class="flex flex-wrap items-center gap-3 px-4 py-4">
          <UiButton
            variant="secondary"
            :disabled="testing === 'webhook'"
            @click="testChannel('webhook')"
          >
            {{ t('settings.testNotification') }}
          </UiButton>
          <span
            v-if="results.webhook === 'sent'"
            role="status"
            class="text-[13px] text-accent"
          >
            {{ t('settings.notificationSent') }}
          </span>
          <span
            v-else-if="results.webhook === 'failed'"
            role="status"
            class="text-[13px] text-danger"
          >
            {{ t('settings.notificationFailed') }}
          </span>
        </div>
      </template>

      <fieldset class="px-4 py-4">
        <legend class="eyebrow text-fg">
          {{ t('settings.notificationEvents') }}
        </legend>
        <p class="mt-1 text-[12px] text-muted">
          {{ t('settings.notificationEventsHint') }}
        </p>
        <div
          role="radiogroup"
          :aria-label="t('settings.notificationEventsFor')"
          class="mt-3 flex flex-wrap gap-4"
        >
          <label
            v-for="channel in channels"
            :key="channel.name"
            class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-fg"
          >
            <input
              v-model="eventChannel"
              type="radio"
              name="notification-event-channel"
              :value="channel.name"
              class="size-4 accent-accent"
            />
            {{ t(channel.labelKey) }}
          </label>
        </div>
        <div class="mt-3 grid gap-3 sm:grid-cols-2">
          <label
            v-for="event in events"
            :key="event.value"
            class="flex min-h-11 cursor-pointer items-center gap-3 text-sm text-fg"
          >
            <input
              v-model="config.channels[eventChannel].events"
              type="checkbox"
              :value="event.value"
              class="size-4 accent-accent"
            />
            {{ t(event.key) }}
          </label>
        </div>
      </fieldset>
    </template>
  </SettingGroup>
</template>

<script setup>
import { ref } from 'vue'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import { notificationTestRequest } from '/src/lib/notificationSettings'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'

const props = defineProps({ config: { type: Object, required: true } })
const { t } = useI18n()
const testing = ref('')
const results = ref({})
const eventChannel = ref('telegram')

const channels = [
  {
    name: 'telegram',
    labelKey: 'settings.telegramEnabled',
    hintKey: 'settings.telegramEnabledHint',
  },
  {
    name: 'ntfy',
    labelKey: 'settings.ntfyEnabled',
    hintKey: 'settings.ntfyEnabledHint',
  },
  {
    name: 'webhook',
    labelKey: 'settings.webhookEnabled',
    hintKey: 'settings.webhookEnabledHint',
  },
]
const events = [
  { value: 'watch.downloaded', key: 'settings.notifyWatchDownloads' },
  { value: 'download.completed', key: 'settings.notifyDownloadCompleted' },
  { value: 'download.failed', key: 'settings.notifyDownloadFailed' },
  { value: 'download.batch', key: 'settings.notifyDownloadBatch' },
  { value: 'upgrade.started', key: 'settings.notifyUpgradeStarted' },
  { value: 'upgrade.finished', key: 'settings.notifyUpgradeFinished' },
  { value: 'upgrade.failed', key: 'settings.notifyUpgradeFailed' },
  { value: 'backup.completed', key: 'settings.notifyBackupCompleted' },
  { value: 'backup.failed', key: 'settings.notifyBackupFailed' },
]

function savedHint(channel, flag) {
  return props.config.channels[channel][flag]
    ? t('settings.notificationSecretSaved')
    : ''
}

async function testChannel(channel) {
  testing.value = channel
  results.value[channel] = ''
  try {
    const res = await API.testNotifications(
      notificationTestRequest(props.config, channel)
    )
    results.value[channel] = res?.data?.ok ? 'sent' : 'failed'
  } catch {
    results.value[channel] = 'failed'
  } finally {
    testing.value = ''
  }
}
</script>
