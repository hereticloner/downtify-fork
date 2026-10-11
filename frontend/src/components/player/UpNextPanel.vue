<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex items-center justify-between gap-3 px-2 pb-3">
      <div class="min-w-0">
        <p class="text-sm font-semibold text-white">{{ t('player.upNext') }}</p>
        <p class="truncate text-xs text-white/55">
          {{ summary }}
        </p>
      </div>
      <button
        v-if="upcoming.length"
        type="button"
        class="shrink-0 rounded-control px-2.5 py-1.5 text-xs font-semibold text-white/70 hover:bg-white/10 hover:text-white"
        @click="player.clearUpcoming()"
      >
        {{ t('player.clearUpcoming') }}
      </button>
    </div>

    <div
      class="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 [scrollbar-width:thin]"
    >
      <div
        v-if="current"
        class="mb-1 flex h-14 items-center gap-3 rounded-[10px] bg-white/10 px-2.5"
      >
        <CoverArt
          :src="current.hasCover ? current.cover : ''"
          :name="current.album || current.title"
          rounded="rounded-[6px]"
          :letter-size="12"
          :icon-size="14"
          class="size-10"
        />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-semibold text-accent">
            {{ current.title }}
          </p>
          <p class="truncate text-xs text-white/55">{{ current.artist }}</p>
        </div>
        <EqBars :size="12" :playing="player.isPlaying.value" />
      </div>

      <TransitionGroup
        name="list"
        tag="ol"
        :aria-label="t('player.upNext')"
        :aria-describedby="
          upcoming.length && !player.shuffle.value ? reorderHintId : undefined
        "
      >
        <li
          v-for="(item, position) in upcoming"
          :key="`${item.track.file}-${item.index}`"
          class="group flex h-14 items-center gap-3 rounded-[10px] px-2.5 transition-colors hover:bg-white/8"
          :class="dragOver === position ? 'bg-white/12' : ''"
          :draggable="!player.shuffle.value"
          @keydown="onRowKeydown($event, item.index)"
          @dragstart="onDragStart($event, item.index)"
          @dragover.prevent="dragOver = position"
          @dragleave="dragOver = -1"
          @drop.prevent="onDrop(item.index)"
          @dragend="dragOver = -1"
        >
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-3 text-left"
            @click="player.playAt(item.index)"
          >
            <CoverArt
              :src="item.track.hasCover ? item.track.cover : ''"
              :name="item.track.album || item.track.title"
              rounded="rounded-[6px]"
              :letter-size="12"
              :icon-size="14"
              class="size-10"
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-white">{{
                item.track.title
              }}</span>
              <span class="block truncate text-xs text-white/55">{{
                item.track.artist
              }}</span>
            </span>
          </button>
          <span class="tabular text-xs text-white/45 group-hover:hidden">
            {{ item.track.duration ? formatDuration(item.track.duration) : '' }}
          </span>
          <div
            v-if="!player.shuffle.value"
            class="hidden items-center group-hover:flex group-focus-within:flex max-sm:flex"
          >
            <button
              type="button"
              class="flex size-8 items-center justify-center rounded-full text-white/60 hover:bg-white/10 hover:text-white disabled:opacity-30"
              :aria-label="t('player.moveUp')"
              :disabled="!reorder.canMove(item.index, -1)"
              @click="reorder.move(item.index, -1)"
            >
              <AppIcon name="chevron-up" :size="16" />
            </button>
            <button
              type="button"
              class="flex size-8 items-center justify-center rounded-full text-white/60 hover:bg-white/10 hover:text-white disabled:opacity-30"
              :aria-label="t('player.moveDown')"
              :disabled="!reorder.canMove(item.index, 1)"
              @click="reorder.move(item.index, 1)"
            >
              <AppIcon name="chevron-down" :size="16" />
            </button>
          </div>
          <button
            type="button"
            class="hidden size-8 items-center justify-center rounded-full text-white/60 hover:bg-white/10 hover:text-white group-hover:flex"
            :aria-label="t('player.removeFromQueue')"
            @click="player.removeAt(item.index)"
          >
            <AppIcon name="x" :size="16" />
          </button>
          <AppIcon
            v-if="!player.shuffle.value"
            name="grip"
            :size="16"
            class="hidden cursor-grab text-white/35 sm:block"
          />
        </li>
      </TransitionGroup>

      <p
        v-if="upcoming.length && !player.shuffle.value"
        :id="reorderHintId"
        class="sr-only"
      >
        {{ t('player.reorderHint') }}
      </p>

      <p
        v-if="!upcoming.length"
        class="px-2 py-8 text-center text-sm text-white/50"
      >
        {{ t('player.queueEnds') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, useId } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import { createQueueReorder } from '/src/lib/queueReorder'
import { usePlayer } from '/src/model/player'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { t } = useI18n()
const dragOver = ref(-1)
let dragFrom = -1

const current = computed(() => player.currentTrack.value)
// Long queues render the first stretch only; the rest is still queued.
const upcoming = computed(() => player.upcoming.value.slice(0, 200))

// The first queued track sits right after the current one: it can't move
// above it, so `min` is the playing index + 1.
const reorderHintId = `reorder-hint-${useId()}`
const reorder = createQueueReorder({
  onMove: (from, to) => player.moveTrack(from, to),
  min: () => player.currentIndex.value + 1,
  max: () => player.playlist.value.length - 1,
})

const summary = computed(() => {
  const rest = player.upcoming.value
  const length = splitLength(
    rest.reduce((sum, item) => sum + (item.track.duration || 0), 0)
  )
  const parts = [t('common.tracks', { count: rest.length })]
  if (length.hours || length.minutes) {
    parts.push(
      length.hours
        ? t('common.lengthHours', length)
        : t('common.lengthMinutes', length)
    )
  }
  return parts.join(' · ')
})

function onDragStart(event, index) {
  dragFrom = index
  event.dataTransfer.effectAllowed = 'move'
}

function onDrop(index) {
  if (dragFrom >= 0 && dragFrom !== index) player.moveTrack(dragFrom, index)
  dragFrom = -1
  dragOver.value = -1
}

// A shuffled queue has no stable order to move within, so the arrow
// shortcut is off then too (the buttons are hidden, drag is disabled).
function onRowKeydown(event, index) {
  if (!player.shuffle.value) reorder.onRowKeydown(event, index)
}
</script>
