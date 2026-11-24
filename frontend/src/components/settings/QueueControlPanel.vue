<template>
  <SettingGroup
    :title="t('settings.queueControlTitle')"
    :description="t('settings.queueControlHint')"
  >
    <SettingRow
      :label="t('settings.queueQuietEnabled')"
      :description="t('settings.queueQuietEnabledHint')"
    >
      <UiSwitch
        v-model="config.quiet_hours.enabled"
        :aria-label="t('settings.queueQuietEnabled')"
      />
    </SettingRow>

    <template v-if="config.quiet_hours.enabled">
      <div class="grid gap-4 px-4 py-4 sm:grid-cols-2">
        <UiInput
          v-model="config.quiet_hours.start"
          :label="t('settings.queueQuietStart')"
          type="time"
          autocomplete="off"
        />
        <UiInput
          v-model="config.quiet_hours.end"
          :label="t('settings.queueQuietEnd')"
          type="time"
          autocomplete="off"
        />
        <UiInput
          v-model.trim="config.quiet_hours.timezone"
          :label="t('settings.queueQuietTimezone')"
          :hint="t('settings.queueQuietTimezoneHint')"
          :placeholder="'Europe/Istanbul'"
          autocomplete="off"
          class="sm:col-span-2"
        />
      </div>
      <p class="px-4 pb-4 text-[12px] leading-relaxed text-muted">
        {{ t('settings.queueQuietBehavior') }}
      </p>
      <p
        v-if="sameTime"
        role="status"
        class="border-t-2 border-line-2 px-4 py-3 text-[12px] text-warn"
      >
        {{ t('settings.queueQuietSameTime') }}
      </p>
    </template>
  </SettingGroup>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '/src/i18n'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'

const props = defineProps({ config: { type: Object, required: true } })
const { t } = useI18n()
const sameTime = computed(
  () =>
    props.config.quiet_hours.enabled &&
    props.config.quiet_hours.start === props.config.quiet_hours.end
)
</script>
