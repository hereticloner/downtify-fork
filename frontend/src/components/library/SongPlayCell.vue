<template>
  <!-- A selectable list's number cell (a link's tracks, an artist's top
       songs): the number, turning into play on hover when the song plays -
       from the library once downloaded, else its 30 s preview clip, whose
       frame fills as the clip goes. On a phone, where the number isn't
       shown, just the play button. -->
  <span
    class="mono flex w-6 shrink-0 items-center justify-center"
    :class="playable ? '' : 'max-sm:hidden'"
  >
    <EqBars v-if="isCurrent" :size="12" :playing="player.isPlaying.value" />
    <button
      v-else-if="previewActive"
      type="button"
      class="relative flex size-6 items-center justify-center overflow-hidden border-2 border-line text-fg"
      :aria-label="playLabel"
      @click.stop="toggle"
    >
      <span
        class="absolute inset-x-0 bottom-0 bg-accent transition-[height] duration-100"
        :style="{ height: `${Math.round(progress * 100)}%` }"
        aria-hidden="true"
      />
      <AppIcon
        :name="previewPlaying ? 'pause' : 'play'"
        :size="9"
        class="relative"
        :class="previewLoading ? 'animate-pulse' : ''"
      />
    </button>
    <template v-else>
      <span
        class="tabular max-sm:hidden"
        :class="playable ? 'group-hover:hidden' : ''"
        >{{ index + 1 }}</span
      >
      <button
        v-if="playable"
        type="button"
        class="text-fg sm:hidden sm:group-hover:block"
        :aria-label="playLabel"
        :title="track ? '' : t('actions.previewLabel')"
        @click.stop="toggle"
      >
        <AppIcon name="play" :size="13" />
      </button>
    </template>
  </span>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import EqBars from '../ui/EqBars.vue'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, required: true },
  // The list's downloaded songs, as library tracks, to queue after this one.
  queue: { type: Array, default: () => [] },
  // The player's "playing from".
  context: { type: Object, default: null },
})

const { t } = useI18n()
const player = usePlayer()
const {
  track,
  isCurrent,
  previewActive,
  previewPlaying,
  previewLoading,
  playable,
  playLabel,
  progress,
  toggle,
} = useSongPlay(props)
</script>
