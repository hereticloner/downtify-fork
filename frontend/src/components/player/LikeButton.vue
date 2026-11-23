<template>
  <UiIconButton
    :icon="liked ? 'heart' : 'heart-outline'"
    :label="liked ? t('likes.unlike') : t('likes.like')"
    :size="size"
    :active="liked"
    toggle
    :disabled="!file"
    class="relative"
    :class="bursting ? 'like-pop' : ''"
    @click.stop="onLike"
  >
    <span v-if="bursting" :key="burstKey" class="like-burst" aria-hidden="true">
      <span class="like-burst-ring" @animationend="clearBurst" />
      <span
        v-for="n in 6"
        :key="n"
        class="like-burst-spark"
        :style="sparkStyle(n)"
      />
    </span>
  </UiIconButton>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { useLikes } from '/src/model/likes'
import { useI18n } from '/src/i18n'
import { prefersReducedMotion } from '/src/lib/viewTransitions'

const props = defineProps({
  // The track's library path, as `GET /tracks` reports it.
  file: { type: String, default: '' },
  size: { type: String, default: 'sm' },
})

const { t } = useI18n()
const likes = useLikes()
const liked = computed(() => likes.isLiked(props.file))

// Six square accent dots; no blur, no glow — just the existing token colour.
const SPARKS = [
  ['-13px', '-11px'],
  ['0px', '-16px'],
  ['13px', '-11px'],
  ['-13px', '11px'],
  ['0px', '16px'],
  ['13px', '11px'],
]

const bursting = ref(false)
const burstKey = ref(0)
let timer

function sparkStyle(n) {
  const [sx, sy] = SPARKS[(n - 1) % SPARKS.length]
  return { '--sx': sx, '--sy': sy }
}

function clearBurst() {
  bursting.value = false
}

function onLike() {
  likes.toggle(props.file)
  if (prefersReducedMotion()) return
  clearTimeout(timer)
  burstKey.value += 1 // a new key restarts the CSS animation on a fast re-tap
  bursting.value = true
  timer = setTimeout(clearBurst, 460)
}

onBeforeUnmount(() => clearTimeout(timer))
</script>
