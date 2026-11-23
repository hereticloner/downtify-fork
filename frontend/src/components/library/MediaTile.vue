<template>
  <!-- One cell of a flush grid: 2px rules on the right/bottom are drawn by
       the tile itself, the grid supplies the top/left ones. Cover sits in a
       frame of its own, the catalogue line below it. -->
  <article
    class="group relative flex min-w-0 flex-col border-r-2 border-b-2 border-line bg-surface transition-colors duration-200 hover:bg-surface-2 motion-reduce:transition-none"
  >
    <div class="relative p-2">
      <RouterLink :to="to" class="block" :aria-label="title">
        <CoverArt
          :src="cover"
          :fallback="fallback"
          :covers="covers"
          :name="name || title"
          :round="round"
          :icon="icon"
          :symbol="symbol"
          :letter-size="round ? 40 : 56"
          class="aspect-square w-full"
        >
          <span
            v-if="playing"
            class="absolute top-0 left-0 flex h-5 items-center gap-1.5 border-l-4 border-accent bg-invert pr-2 pl-1.5 text-on-invert"
          >
            <EqBars :size="9" />
            <span class="eyebrow text-on-invert">{{
              t('player.playing')
            }}</span>
          </span>
          <slot name="badge" />
        </CoverArt>
      </RouterLink>
      <button
        v-if="playable"
        type="button"
        class="play-glow absolute right-3.5 bottom-3.5 flex size-9 items-center justify-center border-2 border-line bg-invert text-on-invert transition-colors duration-100 hover:bg-fg-3 focus-visible:opacity-100 max-md:opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100"
        :aria-label="t('actions.playItem', { name: title })"
        @click="$emit('play')"
      >
        <AppIcon name="play" :size="15" />
      </button>
      <!-- Controls over the cover (e.g. a menu): outside the link, so a
      click on one doesn't also open the tile. -->
      <div v-if="$slots.overlay" class="absolute top-3.5 right-3.5">
        <slot name="overlay" />
      </div>
    </div>
    <RouterLink
      :to="to"
      class="flex min-w-0 flex-1 flex-col gap-1 border-t-2 border-line px-2.5 py-2"
      :class="round ? 'items-center text-center' : ''"
    >
      <span
        class="text-display line-clamp-2 text-[14px] leading-tight font-bold text-fg"
        >{{ title }}</span
      >
      <span class="mono w-full truncate text-muted">{{ subtitle }}</span>
    </RouterLink>
  </article>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import { useI18n } from '/src/i18n'

defineProps({
  to: { type: [String, Object], required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
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
