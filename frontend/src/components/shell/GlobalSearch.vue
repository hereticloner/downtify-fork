<template>
  <form
    role="search"
    class="group relative flex h-9 items-stretch border-2 bg-bg transition-colors duration-100 focus-within:border-accent"
    :class="kind.type === 'link' ? 'border-accent' : 'border-line-2'"
    @submit.prevent="submit"
  >
    <span
      class="flex w-9 shrink-0 items-center justify-center border-r-2"
      :class="
        kind.type === 'link'
          ? 'border-accent text-accent'
          : 'border-line-2 text-faint'
      "
    >
      <AppIcon :name="kind.type === 'link' ? 'link' : 'search'" :size="16" />
    </span>
    <label for="global-search" class="sr-only">{{
      t('search.placeholder')
    }}</label>
    <input
      id="global-search"
      ref="input"
      v-model="text"
      type="search"
      enterkeyhint="search"
      autocomplete="off"
      :placeholder="t('search.placeholder')"
      class="h-full min-w-0 flex-1 bg-transparent px-2.5 text-[13px] text-fg outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
    />
    <button
      v-if="text"
      type="button"
      class="flex w-8 shrink-0 items-center justify-center text-faint transition-colors duration-100 hover:bg-surface-2 hover:text-fg"
      :aria-label="t('common.clear')"
      @click="clear"
    >
      <AppIcon name="x" :size="15" />
    </button>
    <span
      v-if="!text"
      class="mono hidden shrink-0 items-center border-l-2 border-line-2 px-2 text-faint lg:flex"
      >{{ isMac ? '⌘K' : 'Ctrl K' }}</span
    >
    <button
      v-else-if="kind.type === 'link'"
      type="submit"
      class="eyebrow flex shrink-0 items-center gap-1.5 border-l-2 border-line bg-invert px-2.5 text-on-invert"
    >
      <AppIcon name="arrow-up-right" :size="13" stroke-width="2.2" />
      {{ t('search.open') }}
    </button>
  </form>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import { classifyInput } from '/src/lib/input'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const ui = useUi()
const input = ref(null)
const text = ref('')
const isMac =
  typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

const kind = computed(() => classifyInput(text.value))

ui.registerSearchFocus(() => {
  input.value?.focus()
  input.value?.select()
})

// Mirror the page being shown, so the box reads what was searched/pasted.
watch(
  () => [route.name, route.params.query, route.query.url],
  ([name, query, url]) => {
    if (name === 'Search') text.value = String(query || '')
    else if (name === 'Link' || name === 'TopSongs') {
      text.value = String(url || '')
    }
  },
  { immediate: true }
)

function submit() {
  const result = kind.value
  if (result.type === 'search') {
    router.push({ name: 'Search', params: { query: result.query } })
  } else if (result.type === 'link') {
    router.push({ name: 'Link', query: { url: result.url } })
  } else if (result.type === 'unsupported') {
    ui.toast(t('search.unsupportedLink'), { kind: 'error' })
    return
  } else {
    return
  }
  input.value?.blur()
}

function clear() {
  text.value = ''
  input.value?.focus()
}
</script>
