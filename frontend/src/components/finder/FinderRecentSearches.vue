<template>
  <section class="flex min-w-0 flex-col">
    <div class="flex items-stretch border-b border-line-2">
      <h2 class="eyebrow flex min-w-0 flex-1 items-center py-1.5">
        {{ t('search.recent') }}
      </h2>
      <button
        type="button"
        class="eyebrow flex shrink-0 items-center border-l border-line-2 px-3 text-muted transition-colors duration-100 hover:text-fg"
        @click="emit('clear')"
      >
        {{ t('common.clear') }}
      </button>
    </div>
    <div class="flex flex-wrap gap-0.5 pt-2">
      <RouterLink
        v-for="term in terms"
        :key="term"
        :to="{ name: 'Discover', query: { q: term } }"
        class="mono flex h-8 max-w-full items-center gap-2 border px-2.5 transition-colors duration-100"
        :class="
          term === active
            ? 'border-line bg-surface-2 text-fg'
            : 'border-line-2 text-fg-3 hover:border-line hover:text-fg'
        "
        :aria-current="term === active ? 'true' : undefined"
      >
        <!-- The mark is the state: a filled accent square for the search on
             screen, an empty frame for the others. -->
        <span
          class="size-2 shrink-0"
          :class="term === active ? 'bg-accent' : 'border border-line-3'"
          aria-hidden="true"
        />
        <span class="truncate">{{ term }}</span>
      </RouterLink>
    </div>
  </section>
</template>

<script setup>
// The Finder's recent searches, as ruled blocks that run the search again.
// The list itself is the page's (see model/finder.js useRecentSearches).
import { useI18n } from '/src/i18n'

defineProps({
  terms: { type: Array, required: true },
  // The search on screen, marked among them.
  active: { type: String, default: '' },
})
const emit = defineEmits(['clear'])

const { t } = useI18n()
</script>
