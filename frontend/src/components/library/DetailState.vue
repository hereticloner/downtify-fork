<template>
  <div v-if="!loaded" class="border-b-2 border-line">
    <div
      class="grid grid-cols-1 md:grid-cols-[minmax(0,248px)_minmax(0,1fr)] lg:grid-cols-[minmax(0,304px)_minmax(0,1fr)]"
    >
      <div class="border-b-2 border-line p-3 md:border-r-2 md:border-b-0">
        <UiSkeleton
          class="mx-auto aspect-square w-full max-w-56 md:max-w-none"
        />
      </div>
      <div class="flex flex-col justify-center gap-3 p-4 sm:p-6 lg:p-8">
        <UiSkeleton class="h-2.5 w-20" />
        <UiSkeleton class="h-9 w-2/3" />
        <UiSkeleton class="h-3 w-1/2" />
        <UiSkeleton class="mt-3 h-10 w-40" />
      </div>
    </div>
  </div>
  <div v-else-if="!found" class="px-4 py-10 sm:px-6 lg:px-8">
    <UiEmpty :icon="icon" :title="missing" :body="t('library.maybeDeleted')">
      <UiButton :to="{ name: 'Library' }" icon="library">{{
        t('library.backToLibrary')
      }}</UiButton>
    </UiEmpty>
  </div>
  <div v-else class="animate-rise">
    <slot />
  </div>
</template>

<script setup>
import UiButton from '../ui/UiButton.vue'
import UiEmpty from '../ui/UiEmpty.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import { useI18n } from '/src/i18n'

defineProps({
  loaded: { type: Boolean, default: false },
  found: { type: Boolean, default: false },
  icon: { type: String, default: 'music' },
  missing: { type: String, default: '' },
})
const { t } = useI18n()
</script>
