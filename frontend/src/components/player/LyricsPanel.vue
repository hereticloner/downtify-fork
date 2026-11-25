<template>
  <div class="flex h-full min-h-0 flex-col">
    <div
      v-if="lines.length"
      class="flex flex-wrap items-center gap-2 border-b border-line-2 px-2 py-2"
    >
      <span class="eyebrow mr-auto text-muted">
        {{ t('player.lyricsOffset') }}
        <span class="mono ml-1 text-fg">{{ formattedOffset }}</span>
      </span>
      <UiButton size="sm" variant="secondary" @click="adjust(-0.1)">
        −0.1
      </UiButton>
      <UiButton size="sm" variant="secondary" @click="adjust(0.1)">
        +0.1
      </UiButton>
      <UiButton size="sm" variant="ghost" @click="resetOffset">
        {{ t('player.lyricsOffsetReset') }}
      </UiButton>
    </div>

    <div
      v-if="loading"
      class="flex flex-1 flex-col justify-center gap-4 px-2"
      aria-hidden="true"
    >
      <div
        v-for="n in 6"
        :key="n"
        class="h-6 bg-surface-2"
        :class="n % 2 ? 'shimmer' : ''"
        :style="{ width: `${50 + ((n * 37) % 45)}%` }"
      />
    </div>

    <div
      v-else-if="lines.length"
      ref="scroller"
      class="stagger-fade relative flex-1 overflow-y-auto overscroll-contain px-2 py-8 [scrollbar-width:none]"
      @wheel.passive="userScrolled"
      @touchmove.passive="userScrolled"
    >
      <button
        v-for="(line, i) in lines"
        :key="i"
        :ref="(el) => (lineEls[i] = el)"
        type="button"
        class="text-display block w-full border-l-2 py-1.5 pl-3 text-left leading-snug font-semibold transition-colors duration-100"
        :class="[
          compact ? 'text-lg' : 'text-xl lg:text-2xl',
          i === active
            ? 'border-accent text-fg'
            : i < active
              ? 'border-transparent text-faint hover:text-muted'
              : 'border-transparent text-muted hover:text-fg',
        ]"
        @click="player.seek(lyricsSeekTime(line.time, lyricsOffset.value))"
      >
        {{ line.text || '♪' }}
      </button>
    </div>

    <div
      v-else-if="plain"
      class="flex-1 overflow-y-auto px-2 py-6 [scrollbar-width:thin]"
    >
      <p
        class="text-display leading-relaxed font-medium whitespace-pre-line text-fg-3"
      >
        {{ plain }}
      </p>
      <p class="mono mt-6 text-faint">{{ t('player.lyricsNotSynced') }}</p>
    </div>

    <div
      v-else
      class="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center"
    >
      <span
        class="flex size-10 items-center justify-center border border-line-2 text-muted"
      >
        <AppIcon name="lyrics" :size="20" />
      </span>
      <p class="eyebrow text-fg">{{ t('player.noLyrics') }}</p>
      <p class="max-w-xs text-[13px] text-muted">
        {{ t('player.noLyricsHint') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import { usePlayer } from '/src/model/player'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { loadLyrics } from '/src/model/lyrics'
import { activeLineIndex } from '/src/lib/lrc'
import {
  clampLyricsOffset,
  formatLyricsOffset,
  lyricsHighlightTime,
  lyricsSeekTime,
} from '/src/lib/lyricsHealth'
import { useI18n } from '/src/i18n'

const props = defineProps({
  compact: { type: Boolean, default: false },
})

const player = usePlayer()
const { lyricsOffset } = usePlayerPrefs()
const { t } = useI18n()
const loading = ref(false)
const lines = ref([])
const plain = ref('')
const scroller = ref(null)
const lineEls = ref([])
let manualUntil = 0

watch(
  () => player.currentTrack.value?.file,
  async (file) => {
    lines.value = []
    plain.value = ''
    lineEls.value = []
    if (!file) return
    loading.value = true
    const result = await loadLyrics(file)
    if (player.currentTrack.value?.file !== file) return
    lines.value = result.lines
    plain.value = result.plain
    loading.value = false
  },
  { immediate: true }
)

const formattedOffset = computed(() => formatLyricsOffset(lyricsOffset.value))

function adjust(delta) {
  lyricsOffset.value = clampLyricsOffset(lyricsOffset.value + delta)
}

function resetOffset() {
  lyricsOffset.value = 0
}

const active = computed(() =>
  activeLineIndex(
    lines.value,
    lyricsHighlightTime(player.currentTime.value, lyricsOffset.value)
  )
)

function userScrolled() {
  // Leave the user's scroll position alone for a moment.
  manualUntil = Date.now() + 4000
}

watch(active, async (index) => {
  if (index < 0 || Date.now() < manualUntil) return
  await nextTick()
  lineEls.value[index]?.scrollIntoView({ block: 'center', behavior: 'smooth' })
})
</script>
