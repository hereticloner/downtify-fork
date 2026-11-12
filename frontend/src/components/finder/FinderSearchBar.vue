<template>
  <form
    role="search"
    class="flex min-w-0 items-stretch"
    @submit.prevent="submit"
  >
    <span
      class="flex h-12 min-w-0 flex-1 items-center gap-2.5 border-2 border-line bg-bg px-3 transition-colors duration-100 focus-within:border-accent"
    >
      <AppIcon name="search" :size="17" class="text-faint" />
      <label for="finder-search" class="sr-only">{{
        t('finder.placeholder')
      }}</label>
      <input
        id="finder-search"
        ref="input"
        :value="modelValue"
        type="search"
        enterkeyhint="search"
        autocomplete="off"
        :placeholder="t('finder.placeholder')"
        class="mono h-full min-w-0 flex-1 bg-transparent text-fg outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        v-if="modelValue"
        type="button"
        class="flex size-7 shrink-0 items-center justify-center border-l border-line-2 text-faint transition-colors duration-100 hover:text-fg"
        :aria-label="t('common.clear')"
        @click="clear"
      >
        <AppIcon name="x" :size="14" />
      </button>
    </span>
    <!-- The action block shares the field's right rule (-ml-0.5): one 2px
         line between them, not two. -->
    <UiButton
      type="submit"
      variant="primary"
      size="lg"
      class="-ml-0.5"
      :disabled="!modelValue.trim()"
    >
      {{ t('search.searchButton') }}
    </UiButton>
  </form>
</template>

<script setup>
// The Finder's search box, with its own button. It only holds
// the text - `submit` (with the term) and `clear` say what the user did,
// and the page decides what that means.
import { ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'submit', 'clear'])

const { t } = useI18n()
const input = ref(null)

function submit() {
  const term = props.modelValue.trim()
  if (!term) return
  emit('submit', term)
  input.value?.blur()
}

function clear() {
  emit('update:modelValue', '')
  emit('clear')
  input.value?.focus()
}
</script>
