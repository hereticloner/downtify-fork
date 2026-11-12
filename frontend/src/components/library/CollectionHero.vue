<template>
  <header class="border-b-2 border-line bg-surface">
    <div
      class="grid grid-cols-1 md:grid-cols-[minmax(0,248px)_minmax(0,1fr)] lg:grid-cols-[minmax(0,304px)_minmax(0,1fr)]"
    >
      <!-- The plate: a banner when one is set, the cover otherwise. Square
           frame, no wash over it, no overlay text. -->
      <div
        class="relative border-b-2 border-line p-3 md:border-r-2 md:border-b-0"
      >
        <div v-if="banner" class="relative border-2 border-line bg-surface-2">
          <img :src="banner" alt="" class="aspect-video w-full object-cover" />
          <button
            v-if="bannerEditable"
            type="button"
            :title="t('artistArt.editArtist')"
            :aria-label="t('artistArt.editArtist')"
            class="absolute right-0 bottom-0 flex size-9 items-center justify-center border-t-2 border-l-2 border-line bg-bg text-fg transition-colors duration-100 hover:bg-surface-2 active:bg-raised"
            @click="$emit('edit-banner')"
          >
            <AppIcon name="pencil" :size="15" />
          </button>
        </div>
        <div v-else class="relative mx-auto w-full max-w-56 md:max-w-none">
          <CoverArt
            :src="cover"
            :fallback="coverFallback"
            :covers="covers"
            :name="name || title"
            :round="round"
            :icon="icon"
            :symbol="symbol"
            :letter-size="88"
            :icon-size="56"
            class="aspect-square w-full"
          />
          <button
            v-if="photoEditable"
            type="button"
            class="absolute right-0 bottom-0 flex size-9 items-center justify-center border-t-2 border-l-2 border-line bg-bg text-fg transition-colors duration-100 hover:bg-surface-2 active:bg-raised"
            @click="$emit('edit-photo')"
          >
            <span class="sr-only">{{ t('artistArt.editPhoto') }}</span>
            <AppIcon name="pencil" :size="15" />
          </button>
        </div>
      </div>

      <!-- The record: kicker label, title, the mono catalogue line and the
           action blocks. -->
      <div class="flex min-w-0 flex-col justify-center gap-3 p-4 sm:p-6 lg:p-8">
        <span v-if="kicker" class="eyebrow">{{ kicker }}</span>
        <h1
          class="text-display line-clamp-2 text-3xl leading-[1.04] font-bold text-balance break-words sm:text-4xl xl:text-[46px]"
        >
          {{ title }}
        </h1>
        <div
          v-if="$slots.subtitle"
          class="mono flex flex-wrap items-center gap-x-2 gap-y-1 text-fg-3"
        >
          <slot name="subtitle" />
        </div>
        <div
          v-if="$slots.actions"
          class="mt-2 flex flex-wrap items-center gap-2"
        >
          <slot name="actions" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import { useI18n } from '/src/i18n'

defineProps({
  title: { type: String, required: true },
  kicker: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  // Shown when `cover` fails to load (see CoverArt) - for a `cover` that
  // may not exist, like an artist photo from the proxy.
  coverFallback: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  symbol: { type: Boolean, default: false },
  // Kept for the call sites; every plate in this language is square, so
  // nothing about the frame changes with it.
  round: { type: Boolean, default: false },
  // Optional background photo (artist page only - see ArtistView) and
  // whether each "edit photo/banner" affordance is shown at all - each
  // mirrors its own settings toggle independently. When a banner is set,
  // the photo (and its own edit affordance) is hidden entirely to
  // de-clutter the plate - ArtistArtModal's "Profile" tab is still
  // reachable from the banner's edit block.
  banner: { type: String, default: '' },
  photoEditable: { type: Boolean, default: false },
  bannerEditable: { type: Boolean, default: false },
})
defineEmits(['edit-photo', 'edit-banner'])

const { t } = useI18n()
</script>
