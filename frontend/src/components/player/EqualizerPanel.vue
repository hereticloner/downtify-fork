<template>
  <section
    class="flex h-full min-h-0 flex-col gap-4 overflow-y-auto [scrollbar-width:thin]"
    :aria-label="t('player.equalizer')"
  >
    <header class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div class="mr-auto flex min-w-0 items-center gap-2">
        <h2 class="text-display truncate text-lg font-bold">
          {{ t('player.equalizer') }}
        </h2>
        <span
          tabindex="0"
          role="note"
          :title="t('player.experimentalHint')"
          :aria-label="`${t('player.experimental')}: ${t('player.experimentalHint')}`"
          class="mono inline-flex h-[22px] shrink-0 items-center gap-1.5 border border-dashed border-line-3 px-1.5 text-[10px] tracking-[0.06em] whitespace-nowrap text-muted uppercase"
        >
          <AppIcon name="wand" :size="11" />
          {{ t('player.experimental') }}
        </span>
      </div>
      <button
        type="button"
        role="switch"
        :aria-checked="eq.enabled.value"
        :aria-label="t('player.equalizer')"
        :disabled="!eq.supported"
        class="flex h-9 shrink-0 items-center gap-2 border-2 px-2.5 transition-colors duration-100 disabled:opacity-40"
        :class="
          eq.enabled.value
            ? 'border-line bg-invert text-on-invert'
            : 'border-line-2 text-muted hover:border-line hover:text-fg'
        "
        @click="eq.setEnabled(!eq.enabled.value)"
      >
        <span
          class="flex size-4 shrink-0 items-center justify-center border"
          :class="
            eq.enabled.value ? 'border-on-invert text-accent' : 'border-line-3'
          "
          aria-hidden="true"
        >
          <AppIcon
            v-if="eq.enabled.value"
            name="check"
            :size="11"
            stroke-width="3"
          />
        </span>
        <span class="text-[11px] tracking-[0.06em] uppercase">{{
          eq.enabled.value ? t('player.equalizerOn') : t('player.equalizerOff')
        }}</span>
      </button>
    </header>

    <div class="flex flex-wrap items-center gap-2">
      <UiMenu :items="presetMenu" :label="t('player.preset')" align="start">
        <template #trigger>
          <button
            type="button"
            class="flex h-8 items-center gap-2 border-2 border-line-2 px-2.5 text-[11px] tracking-[0.06em] uppercase transition-colors duration-100 hover:border-line hover:bg-surface-2"
            :aria-label="`${t('player.preset')}: ${presetLabel(eq.preset.value)}`"
          >
            <span class="text-faint">{{ t('player.preset') }}</span>
            <span class="text-fg">{{ presetLabel(eq.preset.value) }}</span>
            <AppIcon name="chevron-down" :size="14" class="text-muted" />
          </button>
        </template>
      </UiMenu>
      <button
        type="button"
        class="flex h-8 items-center gap-2 border-2 border-transparent px-2.5 text-[11px] tracking-[0.06em] text-muted uppercase transition-colors duration-100 hover:border-line-2 hover:text-fg disabled:opacity-40"
        :disabled="isDefault"
        @click="eq.reset()"
      >
        <AppIcon name="refresh" :size="14" />{{ t('player.resetEqualizer') }}
      </button>
    </div>

    <p
      v-if="!eq.supported || eq.graphState.value === 'error'"
      class="flex items-center gap-2 text-[13px] text-danger"
    >
      <AppIcon name="alert" :size="15" />
      {{
        eq.supported
          ? t('player.equalizerError')
          : t('player.equalizerUnsupported')
      }}
    </p>

    <div
      class="border-2 border-line bg-surface px-2 pt-3 pb-3 transition-opacity sm:px-4"
      :class="eq.enabled.value ? '' : 'opacity-60'"
    >
      <div class="flex items-stretch gap-1 sm:gap-2">
        <EqBandSlider
          :model-value="eq.preamp.value"
          :limit="PREAMP_LIMIT"
          :label="t('player.preamp')"
          :caption="t('player.preampShort')"
          :height="height"
          class="shrink-0"
          @update:model-value="eq.setPreamp"
        />
        <div class="w-0.5 shrink-0 bg-line-2" aria-hidden="true" />
        <div ref="bandsEl" class="relative min-w-0 flex-1">
          <!-- Response curve, aligned with the slider tracks. Structure
               only: a 2px ink stroke, no fill, no glow. -->
          <svg
            class="pointer-events-none absolute inset-x-0 top-6 overflow-hidden"
            :width="bandsWidth"
            :height="height"
            :viewBox="`0 0 ${bandsWidth} ${height}`"
            aria-hidden="true"
          >
            <path
              v-if="curve"
              :d="curve"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linejoin="miter"
            />
          </svg>
          <div class="relative grid grid-cols-10">
            <EqBandSlider
              v-for="(band, i) in BANDS"
              :key="band.frequency"
              :model-value="eq.gains.value[i]"
              :limit="GAIN_LIMIT"
              :label="t('player.bandLabel', { frequency: band.frequency })"
              :caption="formatFrequency(band.frequency)"
              :height="height"
              @update:model-value="(v) => eq.setGain(i, v)"
            />
          </div>
        </div>
      </div>
    </div>

    <p class="min-h-5 text-[13px] text-muted" aria-live="polite">
      <template v-if="eq.enabled.value && eq.preamp.value > 0">
        {{ t('player.clipWarning') }}
      </template>
      <template v-else-if="eq.enabled.value && eq.headroom.value < -0.05">
        {{
          t('player.headroomHint', {
            amount: Math.round(-eq.headroom.value * 10) / 10,
          })
        }}
      </template>
      <template v-else>{{ t('player.equalizerHint') }}</template>
    </p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import UiMenu from '../ui/UiMenu.vue'
import EqBandSlider from './EqBandSlider.vue'
import { useEqualizer } from '/src/model/equalizer'
import {
  BANDS,
  GAIN_LIMIT,
  PREAMP_LIMIT,
  PRESETS,
  formatFrequency,
  responsePath,
} from '/src/lib/equalizer'
import { useI18n } from '/src/i18n'

defineProps({
  // Cover palette from useCoverPalette, or null. The language has one
  // accent, so the curve no longer takes the artwork's colour.
  palette: { type: Object, default: null },
})

const { t } = useI18n()
const eq = useEqualizer()

const short = useMediaQuery('(max-height: 760px)')
const height = computed(() => (short.value ? 140 : 180))

const bandsEl = ref(null)
const bandsWidth = ref(0)
let observer = null
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    bandsWidth.value = Math.round(entry.contentRect.width)
  })
  observer.observe(bandsEl.value)
})
onBeforeUnmount(() => observer?.disconnect())

const curve = computed(() =>
  bandsWidth.value
    ? responsePath(eq.gains.value, {
        width: bandsWidth.value,
        height: height.value,
      })
    : ''
)

const isDefault = computed(
  () => !eq.enabled.value && eq.preset.value === 'flat' && eq.preamp.value === 0
)

function presetLabel(id) {
  return t(`player.presets.${id}`)
}

const presetMenu = computed(() => [
  ...PRESETS.map((preset) => ({
    label: presetLabel(preset.id),
    checked: eq.preset.value === preset.id,
    action: () => eq.selectPreset(preset.id),
  })),
  { divider: true, hidden: !eq.isCustom.value },
  {
    label: presetLabel('custom'),
    checked: true,
    disabled: true,
    hidden: !eq.isCustom.value,
  },
])
</script>
