<template>
  <!-- List-view row: 72px block, cover on a frame, title over its catalogue
       line. The row draws only its bottom hairline; the list frame owns the
       outer 2px rules. -->
  <div
    class="group flex h-[72px] items-center gap-4 border-b border-line-2 px-3 transition-[background-color,transform] duration-200 hover:bg-surface-2 motion-safe:hover:translate-x-0.5 motion-reduce:transition-none last:border-b-0"
  >
    <RouterLink :to="to" class="flex min-w-0 flex-1 items-center gap-3">
      <CoverArt
        :src="cover"
        :fallback="fallback"
        :covers="covers"
        :name="name || title"
        :round="round"
        :icon="icon"
        :symbol="symbol"
        :letter-size="18"
        :icon-size="18"
        class="size-12"
      />
      <span class="flex min-w-0 flex-1 flex-col gap-0.5">
        <span class="flex items-center gap-2">
          <span class="truncate text-[15px] font-semibold text-fg">{{
            title
          }}</span>
          <EqBars v-if="playing" :size="10" />
        </span>
        <span class="mono truncate text-muted">{{ subtitle }}</span>
      </span>
    </RouterLink>
    <div class="hidden min-w-0 items-center gap-2 md:flex">
      <slot name="meta" />
    </div>
    <span v-if="aside" class="mono tabular hidden w-24 text-right sm:block">
      {{ aside }}
    </span>
    <div class="flex items-center gap-1">
      <slot name="actions" />
      <UiIconButton
        v-if="playable"
        icon="play"
        :label="t('actions.playItem', { name: title })"
        size="sm"
        class="opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100"
        @click="$emit('play')"
      />
    </div>
  </div>
</template>

<script setup>
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useI18n } from '/src/i18n'

defineProps({
  to: { type: [String, Object], required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  aside: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  // Shown when `cover` fails to load (see CoverArt).
  fallback: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  symbol: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
  playable: { type: Boolean, default: true },
})
defineEmits(['play'])
const { t } = useI18n()
</script>
