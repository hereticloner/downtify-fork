<template>
  <div class="flex flex-col">
    <section
      v-for="group in groups"
      :key="group.id"
      class="flex flex-col border-b-2 border-line"
      :aria-label="group.title"
    >
      <h2
        class="eyebrow flex h-10 items-center border-b border-line-2 bg-surface-2 px-3 text-fg"
      >
        {{ group.title }}
      </h2>
      <ul class="grid border-l-2 border-line sm:grid-cols-2 xl:grid-cols-3">
        <li
          v-for="link in group.links"
          :key="link.key"
          class="border-r-2 border-b border-line"
        >
          <a
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="group flex h-full items-center gap-3 px-3 py-3 transition-colors duration-100 hover:bg-surface-2"
          >
            <span
              class="grid size-9 shrink-0 place-items-center border-2 border-line bg-surface-2 text-fg"
            >
              <AppIcon :name="link.icon" :size="16" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold">{{
                link.label
              }}</span>
              <span class="mono block truncate text-faint">{{
                linkHost(link.url)
              }}</span>
            </span>
            <AppIcon
              name="arrow-up-right"
              :size="15"
              class="shrink-0 text-faint transition-colors duration-100 group-hover:text-fg"
            />
          </a>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
// The artist's Links tab: every profile link, as a ruled row of blocks - the
// streaming platforms they were found on, then the social networks they
// filled in. Each block is one external link (see lib/artistLinks.js for what
// a link is).
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import { linkHost } from '/src/lib/artistLinks'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // `artistPlatformLinks(...)` and `artistSocialLinks(...)`.
  platforms: { type: Array, default: () => [] },
  social: { type: Array, default: () => [] },
})

const { t } = useI18n()

const groups = computed(() =>
  [
    {
      id: 'platforms',
      title: t('artist.linksPlatforms'),
      links: props.platforms,
    },
    { id: 'social', title: t('artist.linksSocial'), links: props.social },
  ].filter((group) => group.links.length)
)
</script>
