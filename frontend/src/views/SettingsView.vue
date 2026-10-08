<template>
  <div
    class="mx-auto flex max-w-[1280px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader
      :title="t('settings.title')"
      :subtitle="t('settings.subtitle')"
    />

    <div class="grid items-start gap-8 lg:grid-cols-[220px_minmax(0,1fr)]">
      <!-- Section navigation -->
      <nav
        class="-mx-4 flex gap-1 overflow-x-auto px-4 [scrollbar-width:none] lg:sticky lg:top-[96px] lg:mx-0 lg:flex-col lg:px-0"
        :aria-label="t('settings.sections')"
      >
        <RouterLink
          v-for="item in sections"
          :key="item.id"
          :to="{ name: 'Settings', params: { section: item.id } }"
          replace
          class="flex h-10 shrink-0 items-center gap-2.5 rounded-control px-3 text-sm whitespace-nowrap transition-colors"
          :class="
            section === item.id
              ? 'bg-surface-2 font-semibold text-fg'
              : 'font-medium text-muted hover:bg-surface-2/60 hover:text-fg'
          "
        >
          <AppIcon
            :name="item.icon"
            :size="17"
            :class="section === item.id ? 'text-accent' : ''"
          />
          {{ item.label }}
          <ExperimentalBadge v-if="item.experimental" class="lg:ml-auto" />
        </RouterLink>
      </nav>

      <div v-if="!sm.loaded.value" class="flex flex-col gap-3">
        <UiSkeleton v-for="n in 4" :key="n" class="h-20 !rounded-panel" />
      </div>

      <Transition v-else name="page" mode="out-in">
        <div :key="section" class="flex min-w-0 flex-col gap-8">
          <!-- General -->
          <template v-if="section === 'general'">
            <AccountSettings v-if="!auth.authDisabled.value" />
            <SettingGroup
              :title="t('settings.appearance')"
              :description="t('settings.personalHint')"
            >
              <SettingRow
                :label="t('settings.theme')"
                :description="t('settings.themeHint')"
              >
                <UiSegmented
                  :model-value="theme.mode.value"
                  show-labels
                  :options="[
                    {
                      value: 'dark',
                      icon: 'moon',
                      label: t('settings.themeDark'),
                    },
                    {
                      value: 'light',
                      icon: 'sun',
                      label: t('settings.themeLight'),
                    },
                    {
                      value: 'system',
                      icon: 'monitor',
                      label: t('settings.themeSystem'),
                    },
                  ]"
                  @update:model-value="theme.setMode"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.language')"
                :description="t('settings.languageHint')"
              >
                <UiSelect
                  :model-value="locale"
                  :options="
                    locales.map((l) => ({ value: l.code, label: l.name }))
                  "
                  :label="t('settings.language')"
                  icon="globe"
                  @update:model-value="setLocale"
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.playerGroup')">
              <!-- Yours, and applied at once like the theme: it isn't part
                   of what "Save" sends to the server (model/account.js). -->
              <SettingRow
                :label="t('settings.showLyrics')"
                :description="t('settings.showLyricsHint')"
              >
                <UiSwitch
                  v-model="showLyrics"
                  :aria-label="t('settings.showLyrics')"
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.searchGroup')">
              <SettingRow
                :label="t('settings.searchAlbums')"
                :description="t('settings.searchAlbumsHint')"
              >
                <UiSwitch
                  v-model="account.searchAlbums.value"
                  :aria-label="t('settings.searchAlbums')"
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.shortcutsGroup')">
              <SettingRow
                :label="t('shortcuts.title')"
                :description="t('settings.shortcutsHint')"
              >
                <UiButton
                  variant="ghost"
                  icon="keyboard"
                  @click="openShortcuts"
                >
                  {{ t('settings.showShortcuts') }}
                </UiButton>
              </SettingRow>
            </SettingGroup>
          </template>

          <!-- Audio sources -->
          <template v-else-if="section === 'sources'">
            <SettingGroup
              :title="t('settings.sourcesTitle')"
              :description="t('settings.sourcesHint')"
            >
              <SourceOrder v-model="s.audio_providers" />
            </SettingGroup>

            <SettingGroup :title="t('settings.youtubeTitle')">
              <CookiesCard />
            </SettingGroup>
          </template>

          <!-- Downloads & files -->
          <template v-else-if="section === 'files'">
            <SettingGroup :title="t('settings.audioGroup')">
              <SettingRow
                :label="t('settings.format')"
                :description="t('settings.formatHint')"
              >
                <UiSegmented
                  v-model="s.format"
                  show-labels
                  :options="
                    sm.settingsOptions.format.map((f) => ({
                      value: f,
                      label: f.toUpperCase(),
                    }))
                  "
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.bitrate')"
                :description="
                  s.format === 'flac'
                    ? t('settings.bitrateLossless')
                    : t('settings.bitrateHint')
                "
              >
                <UiSegmented
                  v-model="s.bitrate"
                  show-labels
                  :class="
                    s.format === 'flac' ? 'pointer-events-none opacity-40' : ''
                  "
                  :options="
                    sm.settingsOptions.bitrate.map((b) => ({
                      value: b,
                      label: `${b}k`,
                    }))
                  "
                />
              </SettingRow>
            </SettingGroup>

            <SettingGroup :title="t('settings.filesGroup')">
              <SettingRow
                :label="t('settings.template')"
                :description="t('settings.templateHint')"
                stacked
              >
                <div class="flex w-full flex-col gap-2">
                  <div class="flex gap-2">
                    <UiInput
                      v-model.trim="s.output"
                      class="flex-1"
                      :placeholder="sm.settingsOptions.output"
                      mono
                    />
                    <UiButton
                      variant="ghost"
                      @click="s.output = sm.settingsOptions.output"
                    >
                      {{ t('settings.reset') }}
                    </UiButton>
                  </div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="token in templateTokens"
                      :key="token"
                      type="button"
                      class="rounded-md border border-line-3 bg-surface-2 px-2 py-1 font-mono text-xs text-fg-3 hover:border-accent hover:text-accent"
                      @click="addToken(token)"
                    >
                      {{ token }}
                    </button>
                  </div>
                  <p class="text-xs text-muted">
                    {{ t('settings.templatePreview') }}
                    <span class="font-mono text-fg-3">{{
                      templatePreview
                    }}</span>
                  </p>
                </div>
              </SettingRow>
              <SettingRow
                :label="t('settings.byArtist')"
                :description="t('settings.byArtistHint')"
              >
                <UiSwitch
                  v-model="s.organize_by_artist"
                  :aria-label="t('settings.byArtist')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.byAlbum')"
                :description="t('settings.byAlbumHint')"
              >
                <UiSwitch
                  v-model="s.organize_by_album"
                  :aria-label="t('settings.byAlbum')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.overwrite')"
                :description="t('settings.overwriteHint')"
              >
                <UiSwitch
                  v-model="s.overwrite_existing_files"
                  :aria-label="t('settings.overwrite')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.m3u')"
                :description="t('settings.m3uHint')"
              >
                <UiSwitch
                  v-model="s.generate_m3u"
                  :aria-label="t('settings.m3u')"
                />
              </SettingRow>
              <!-- The cover is saved next to the .m3u, so it only has
                   somewhere to go while playlist files are written. -->
              <SettingRow
                v-if="s.generate_m3u"
                :label="t('settings.playlistCover')"
                :description="t('settings.playlistCoverHint')"
              >
                <UiSwitch
                  v-model="s.download_cover_art_playlists"
                  :aria-label="t('settings.playlistCover')"
                />
              </SettingRow>
              <!-- Saved once, the first time an artist's page is opened;
                   the artist edit modal can always pick either by hand. -->
              <SettingRow
                :label="t('settings.artistCover')"
                :description="t('settings.artistCoverHint')"
              >
                <UiSwitch
                  v-model="s.download_cover_art_artist"
                  :aria-label="t('settings.artistCover')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.artistCoverBanner')"
                :description="t('settings.artistCoverBannerHint')"
              >
                <UiSwitch
                  v-model="s.download_cover_art_artist_banner"
                  :aria-label="t('settings.artistCoverBanner')"
                />
              </SettingRow>
            </SettingGroup>

            <SettingGroup :title="t('settings.ytGroup')">
              <SettingRow
                :label="t('settings.ytClients')"
                :description="t('settings.ytClientsHint')"
                stacked
              >
                <UiInput
                  :model-value="(s.yt_player_clients || []).join(', ')"
                  :placeholder="t('settings.ytClientsPlaceholder')"
                  :aria-label="t('settings.ytClients')"
                  @update:model-value="
                    (v) =>
                      (s.yt_player_clients = String(v || '')
                        .split(',')
                        .map((part) => part.trim())
                        .filter(Boolean))
                  "
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.ytPoTokens')"
                :description="t('settings.ytPoTokensHint')"
                stacked
              >
                <UiInput
                  :model-value="(s.yt_po_tokens || []).join(', ')"
                  :placeholder="t('settings.ytPoTokensPlaceholder')"
                  :aria-label="t('settings.ytPoTokens')"
                  @update:model-value="
                    (v) =>
                      (s.yt_po_tokens = String(v || '')
                        .split(',')
                        .map((part) => part.trim())
                        .filter(Boolean))
                  "
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.pacingGroup')">
              <SettingRow
                :label="t('settings.parallel')"
                :description="t('settings.parallelHint')"
                stacked
              >
                <PresetPicker
                  :model-value="s.max_parallel_downloads"
                  :presets="sm.settingsOptions.max_parallel_downloads_presets"
                  :min="sm.settingsOptions.max_parallel_downloads_min"
                  :max="sm.settingsOptions.max_parallel_downloads_max"
                  :custom-label="t('settings.custom')"
                  @update:model-value="
                    (v) =>
                      (s.max_parallel_downloads = clampParallelDownloads(v))
                  "
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.delay')"
                :description="t('settings.delayHint')"
                stacked
              >
                <PresetPicker
                  :model-value="s.download_delay_seconds"
                  :presets="sm.settingsOptions.download_delay_seconds_presets"
                  :min="sm.settingsOptions.download_delay_seconds_min"
                  :max="sm.settingsOptions.download_delay_seconds_max"
                  unit="s"
                  :format="(v) => `${v}s`"
                  :custom-label="t('settings.custom')"
                  @update:model-value="
                    (v) =>
                      (s.download_delay_seconds = clampDownloadDelaySeconds(v))
                  "
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.syncDelay')"
                :description="t('settings.syncDelayHint')"
                stacked
              >
                <PresetPicker
                  :model-value="s.external_sync_delay_seconds"
                  :presets="
                    sm.settingsOptions.external_sync_delay_seconds_presets
                  "
                  :min="sm.settingsOptions.external_sync_delay_seconds_min"
                  :max="sm.settingsOptions.external_sync_delay_seconds_max"
                  unit="s"
                  :format="(v) => `${v}s`"
                  :custom-label="t('settings.custom')"
                  @update:model-value="
                    (v) =>
                      (s.external_sync_delay_seconds =
                        clampExternalSyncDelaySeconds(v))
                  "
                />
              </SettingRow>
            </SettingGroup>
          </template>

          <!-- Tags, art, lyrics -->
          <template v-else-if="section === 'tags'">
            <SettingGroup :title="t('settings.artGroup')">
              <SettingRow
                :label="t('settings.coverArt')"
                :description="t('settings.coverArtHint')"
              >
                <UiSwitch
                  v-model="s.download_cover_art"
                  :aria-label="t('settings.coverArt')"
                />
              </SettingRow>
              <SettingRow
                v-if="s.download_cover_art"
                :label="t('settings.coverSize')"
                :description="t('settings.coverSizeHint')"
                stacked
              >
                <PresetPicker
                  :model-value="s.cover_resolution"
                  :presets="sm.settingsOptions.cover_resolution_presets"
                  :min="sm.settingsOptions.cover_resolution_min"
                  :max="sm.settingsOptions.cover_resolution_max"
                  unit="px"
                  :custom-label="t('settings.custom')"
                  @update:model-value="
                    (v) => (s.cover_resolution = clampCoverResolution(v))
                  "
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.lyricsGroup')">
              <SettingRow
                :label="t('settings.lyrics')"
                :description="t('settings.lyricsHint')"
              >
                <UiSwitch
                  v-model="s.download_lyrics"
                  :aria-label="t('settings.lyrics')"
                />
              </SettingRow>
              <SettingRow
                v-if="s.download_lyrics"
                :label="t('settings.lyricsLrcBeside')"
                :description="t('settings.lyricsLrcBesideHint')"
              >
                <UiSwitch
                  v-model="s.lyrics_lrc_beside"
                  :aria-label="t('settings.lyricsLrcBeside')"
                />
              </SettingRow>
              <SettingRow
                v-if="s.download_lyrics && !s.lyrics_lrc_beside"
                :label="t('settings.lyricsLrcFolder')"
                :description="t('settings.lyricsLrcFolderHint')"
                stacked
              >
                <PathSuggestInput
                  v-model="s.lyrics_lrc_dir"
                  :placeholder="t('settings.lyricsLrcFolderPlaceholder')"
                />
              </SettingRow>
              <SettingRow
                v-if="s.download_lyrics"
                :label="t('settings.lyricsProviders')"
                :description="t('settings.lyricsProvidersHint')"
                stacked
              >
                <LyricsOrder
                  v-model="s.lyrics_providers"
                  class="-mx-4 w-full"
                />
              </SettingRow>
            </SettingGroup>
          </template>

          <!-- Navidrome -->
          <template v-else-if="section === 'navidrome'">
            <SettingGroup
              :title="t('settings.navidromeTitle')"
              :description="t('settings.navidromeHint')"
            >
              <SettingRow
                :label="t('settings.navidromeEnabled')"
                :description="t('settings.navidromeEnabledHint')"
              >
                <UiSwitch
                  v-model="s.navidrome.enabled"
                  :aria-label="t('settings.navidromeEnabled')"
                />
              </SettingRow>
              <template v-if="s.navidrome.enabled">
                <div class="grid gap-4 px-5 py-4 sm:grid-cols-2">
                  <UiInput
                    v-model.trim="s.navidrome.url"
                    class="sm:col-span-2"
                    :label="t('settings.navidromeUrl')"
                    placeholder="http://navidrome:4533"
                    type="url"
                    :error="needsValue(s.navidrome.url)"
                  />
                  <UiInput
                    v-model.trim="s.navidrome.username"
                    :label="t('settings.navidromeUser')"
                    autocomplete="username"
                    :error="needsValue(s.navidrome.username)"
                  />
                  <UiInput
                    v-model="s.navidrome.password"
                    :label="t('settings.navidromePassword')"
                    type="password"
                    autocomplete="current-password"
                    :error="needsValue(s.navidrome.password)"
                  />
                  <UiInput
                    v-model.trim="s.navidrome.admin_username"
                    :label="t('settings.navidromeAdminUser')"
                    :hint="t('settings.navidromeAdminHint')"
                  />
                  <UiInput
                    v-model="s.navidrome.admin_password"
                    :label="t('settings.navidromeAdminPassword')"
                    type="password"
                  />
                </div>
                <div class="px-5 py-4">
                  <ConnectionTest
                    kind="navidrome"
                    :config="s.navidrome"
                    :url="s.navidrome.url"
                  />
                </div>
                <SettingRow
                  :label="t('settings.navidromeSync')"
                  :description="t('settings.navidromeSyncHint')"
                >
                  <UiSwitch
                    v-model="s.sync_navidrome"
                    :aria-label="t('settings.navidromeSync')"
                  />
                </SettingRow>
                <SettingRow :label="t('settings.navidromePublic')">
                  <UiSwitch
                    v-model="s.navidrome.public_playlist"
                    :aria-label="t('settings.navidromePublic')"
                  />
                </SettingRow>
              </template>
            </SettingGroup>
          </template>

          <!-- Notifications -->
          <template v-else-if="section === 'notifications'">
            <SettingGroup
              :title="t('settings.notificationsTitle')"
              :description="t('settings.notificationsHint')"
            >
              <SettingRow
                :label="t('settings.notificationsEnabled')"
                :description="t('settings.notificationsEnabledHint')"
              >
                <UiSwitch
                  v-model="s.notifications.enabled"
                  :aria-label="t('settings.notificationsEnabled')"
                />
              </SettingRow>
              <template v-if="s.notifications.enabled">
                <SettingRow
                  :label="t('settings.telegramEnabled')"
                  :description="t('settings.telegramEnabledHint')"
                >
                  <UiSwitch
                    v-model="s.notifications.telegram_enabled"
                    :aria-label="t('settings.telegramEnabled')"
                  />
                </SettingRow>
                <template v-if="s.notifications.telegram_enabled">
                  <div class="grid gap-4 px-5 py-4 sm:grid-cols-2">
                    <UiInput
                      v-model="s.notifications.telegram_bot_token"
                      :label="t('settings.telegramBotToken')"
                      autocomplete="off"
                    />
                    <UiInput
                      v-model.trim="s.notifications.telegram_chat_id"
                      :label="t('settings.telegramChatId')"
                      :hint="t('settings.telegramChatIdHint')"
                      autocomplete="off"
                    />
                  </div>
                  <div class="flex flex-wrap items-center gap-3 px-5 py-4">
                    <UiButton
                      variant="ghost"
                      :disabled="notificationTest === 'sending'"
                      @click="sendTestNotification"
                    >
                      {{ t('settings.testNotification') }}
                    </UiButton>
                    <span
                      v-if="notificationTest === 'sent'"
                      class="text-sm text-accent"
                    >
                      {{ t('settings.notificationSent') }}
                    </span>
                    <span
                      v-else-if="notificationTest === 'failed'"
                      class="text-sm text-red-500"
                    >
                      {{ t('settings.notificationFailed') }}
                    </span>
                  </div>
                  <SettingRow
                    :label="t('settings.notifyWatchDownloads')"
                    :description="t('settings.notifyWatchDownloadsHint')"
                  >
                    <UiSwitch
                      v-model="s.notifications.notify_watch_downloads"
                      :aria-label="t('settings.notifyWatchDownloads')"
                    />
                  </SettingRow>
                </template>
              </template>
            </SettingGroup>
          </template>

          <!-- Scrobbling -->
          <template v-else-if="section === 'scrobbling'">
            <SettingGroup
              :title="t('settings.scrobblingTitle')"
              :description="t('settings.scrobblingHint')"
            >
              <SettingRow
                :label="t('settings.scrobblingEnabled')"
                :description="t('settings.scrobblingEnabledHint')"
              >
                <UiSwitch
                  v-model="s.scrobbling.enabled"
                  :aria-label="t('settings.scrobblingEnabled')"
                />
              </SettingRow>
              <template v-if="s.scrobbling.enabled">
                <SettingRow
                  :label="t('settings.lastfmEnabled')"
                  :description="t('settings.lastfmEnabledHint')"
                >
                  <UiSwitch
                    v-model="s.scrobbling.lastfm_enabled"
                    :aria-label="t('settings.lastfmEnabled')"
                  />
                </SettingRow>
                <template v-if="s.scrobbling.lastfm_enabled">
                  <div class="grid gap-4 px-5 py-4 sm:grid-cols-2">
                    <UiInput
                      v-model.trim="s.scrobbling.lastfm_api_key"
                      :label="t('settings.lastfmApiKey')"
                      autocomplete="off"
                    />
                    <UiInput
                      v-model.trim="s.scrobbling.lastfm_api_secret"
                      :label="t('settings.lastfmApiSecret')"
                      autocomplete="off"
                    />
                  </div>
                  <div class="flex flex-wrap items-center gap-3 px-5 py-4">
                    <template v-if="!s.scrobbling.lastfm_session_key">
                      <UiButton
                        variant="ghost"
                        :disabled="lastfmAuth.busy"
                        @click="startLastfmAuth"
                      >
                        {{ t('settings.connectLastfm') }}
                      </UiButton>
                      <a
                        v-if="lastfmAuth.url"
                        :href="lastfmAuth.url"
                        target="_blank"
                        rel="noopener"
                        class="text-sm text-accent underline"
                      >
                        {{ t('settings.authorizeLastfm') }}
                      </a>
                      <UiButton
                        v-if="lastfmAuth.token"
                        variant="ghost"
                        :disabled="lastfmAuth.busy"
                        @click="finishLastfmAuth"
                      >
                        {{ t('settings.finishLastfm') }}
                      </UiButton>
                    </template>
                    <template v-else>
                      <span class="text-sm text-accent">
                        {{
                          t('settings.lastfmConnected', {
                            username: s.scrobbling.lastfm_username,
                          })
                        }}
                      </span>
                      <UiButton
                        variant="ghost"
                        :disabled="scrobblingTest === 'testing'"
                        @click="runScrobblingTest"
                      >
                        {{ t('settings.testConnection') }}
                      </UiButton>
                      <UiButton variant="ghost" @click="disconnectLastfm">
                        {{ t('settings.disconnectLastfm') }}
                      </UiButton>
                    </template>
                    <span
                      v-if="scrobblingTest === 'ok'"
                      class="text-sm text-accent"
                    >
                      {{ t('settings.scrobblingOk') }}
                    </span>
                    <span
                      v-else-if="scrobblingTest === 'failed'"
                      class="text-sm text-red-500"
                    >
                      {{ t('settings.scrobblingFailed') }}
                    </span>
                  </div>
                  <SettingRow
                    :label="t('settings.scrobbleNowPlaying')"
                    :description="t('settings.scrobbleNowPlayingHint')"
                  >
                    <UiSwitch
                      v-model="s.scrobbling.scrobble_now_playing"
                      :aria-label="t('settings.scrobbleNowPlaying')"
                    />
                  </SettingRow>
                </template>
              </template>
            </SettingGroup>
          </template>

          <!-- Storage -->
          <template v-else-if="section === 'storage'">
            <SettingGroup
              :title="t('settings.storageTitle')"
              :description="t('settings.storageHint')"
            >
              <SettingRow
                :label="t('settings.diskUsage')"
                :description="`${t('settings.diskUsed')}: ${formatBytes(
                  storage.disk.used
                )} / ${formatBytes(storage.disk.total)}`"
              >
                <div class="flex w-full items-center gap-2">
                  <div class="h-2 flex-1 rounded-full bg-surface">
                    <div
                      class="h-2 rounded-full bg-accent"
                      :style="{
                        width: `${storage.disk.percent}%`,
                      }"
                    />
                  </div>
                  <span class="text-sm tabular-nums">
                    {{ storage.disk.percent }}%
                  </span>
                </div>
              </SettingRow>
              <SettingRow
                :label="t('settings.librarySize')"
                :description="`${formatBytes(
                  storage.library.bytes
                )} · ${storage.library.tracks} ${t('settings.tracks')}`"
              >
                <UiButton
                  variant="ghost"
                  :disabled="storageLoading"
                  @click="loadStorage"
                >
                  {{ t('settings.refresh') }}
                </UiButton>
              </SettingRow>
              <div class="px-5 py-4">
                <div class="mb-2 flex items-center justify-between">
                  <h3 class="text-sm font-medium">
                    {{ t('settings.duplicates') }}
                  </h3>
                  <span class="text-sm text-muted">
                    {{
                      storage.duplicates.groups.length
                        ? `${t('settings.wastedSpace')}: ${formatBytes(
                            storage.duplicates.total_wasted_bytes
                          )}`
                        : ''
                    }}
                  </span>
                </div>
                <p class="mb-3 text-sm text-muted">
                  {{ t('settings.duplicatesHint') }}
                </p>
                <div v-if="storageLoading" class="text-sm text-muted">
                  {{ t('settings.refreshing') }}
                </div>
                <div
                  v-else-if="!storage.duplicates.groups.length"
                  class="text-sm text-muted"
                >
                  {{ t('settings.noDuplicates') }}
                </div>
                <div v-else class="flex flex-col gap-2">
                  <div
                    v-for="group in storage.duplicates.groups"
                    :key="group.key"
                    class="rounded-lg border border-surface p-3"
                  >
                    <div class="flex items-center justify-between gap-2">
                      <div class="min-w-0">
                        <div class="truncate text-sm font-medium">
                          {{ group.artist }} - {{ group.title }}
                        </div>
                        <div v-if="group.album" class="text-sm text-muted">
                          {{ group.album }}
                        </div>
                      </div>
                      <span class="text-sm text-muted tabular-nums">
                        +{{ formatBytes(group.wasted_bytes) }}
                      </span>
                    </div>
                    <div class="mt-2 flex flex-col gap-1">
                      <div class="flex items-center justify-between text-sm">
                        <span class="truncate text-muted">
                          {{ group.keep.file }}
                        </span>
                        <span class="text-accent">
                          {{ t('settings.keep') }}
                        </span>
                      </div>
                      <div
                        v-for="dup in group.duplicates"
                        :key="dup.file"
                        class="flex items-center justify-between text-sm"
                      >
                        <span class="truncate text-muted">
                          {{ dup.file }}
                        </span>
                        <span class="text-red-500">
                          {{ formatBytes(dup.size) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <div
                  v-if="storage.duplicates.groups.length"
                  class="mt-3 flex items-center gap-3"
                >
                  <UiButton
                    variant="ghost"
                    :disabled="storageDeleting"
                    @click="deleteDuplicates"
                  >
                    {{
                      storageDeleting
                        ? t('settings.deleting')
                        : t('settings.deleteDuplicates')
                    }}
                  </UiButton>
                  <span
                    v-if="storageMessage"
                    :class="
                      storageMessageOk
                        ? 'text-sm text-accent'
                        : 'text-sm text-red-500'
                    "
                  >
                    {{ storageMessage }}
                  </span>
                </div>
              </div>
            </SettingGroup>
          </template>

          <!-- Spotify Mirror -->
          <template v-else-if="section === 'spotify'">
            <SettingGroup
              :title="t('settings.spotifyMirrorTitle')"
              :description="t('settings.spotifyMirrorHint')"
            >
              <SettingRow
                :label="t('settings.spotifyMirrorEnabled')"
                :description="t('settings.spotifyMirrorEnabledHint')"
              >
                <UiSwitch
                  v-model="s.spotify_mirror.enabled"
                  :aria-label="t('settings.spotifyMirrorEnabled')"
                />
              </SettingRow>
              <template v-if="s.spotify_mirror.enabled">
                <div class="grid gap-4 px-5 py-4 sm:grid-cols-2">
                  <UiInput
                    v-model.trim="s.spotify_mirror.client_id"
                    :label="t('settings.spotifyMirrorClientId')"
                    :hint="t('settings.spotifyMirrorClientIdHint')"
                    autocomplete="off"
                  />
                  <UiInput
                    v-model.trim="s.spotify_mirror.redirect_uri"
                    :label="t('settings.spotifyMirrorRedirect')"
                    :hint="t('settings.spotifyMirrorRedirectHint')"
                    autocomplete="off"
                  />
                </div>
                <div
                  v-if="spotifyConnected"
                  class="flex flex-wrap items-center gap-3 px-5 pb-4"
                >
                  <UiButton
                    variant="ghost"
                    :disabled="spotifyDevicesLoading"
                    @click="loadSpotifyDevices"
                  >
                    {{ t('settings.spotifyMirrorLoadDevices') }}
                  </UiButton>
                  <UiSelect
                    v-if="spotifyDevices.length"
                    v-model="s.spotify_mirror.device_id"
                    :options="spotifyDevices"
                    :label="t('settings.spotifyMirrorDevice')"
                    size="sm"
                  />
                </div>
                <div class="flex flex-wrap items-center gap-3 px-5 pb-4">
                  <UiButton
                    variant="ghost"
                    :disabled="spotifyConnected"
                    @click="connectSpotify"
                  >
                    {{ t('settings.spotifyMirrorConnect') }}
                  </UiButton>
                  <UiButton
                    variant="ghost"
                    :disabled="spotifyTest === 'testing'"
                    @click="runSpotifyMirrorTest"
                  >
                    {{ t('settings.testConnection') }}
                  </UiButton>
                  <span v-if="spotifyTest === 'ok'" class="text-sm text-accent">
                    {{ spotifyMirrorOkLabel }}
                  </span>
                  <span
                    v-else-if="spotifyTest === 'failed'"
                    class="text-sm text-red-500"
                  >
                    {{ t('settings.spotifyMirrorFailed') }}
                  </span>
                </div>
                <SettingRow
                  :label="t('settings.spotifyMirrorSilent')"
                  :description="t('settings.spotifyMirrorSilentHint')"
                >
                  <UiSwitch
                    v-model="s.spotify_mirror.silent_on_target"
                    :aria-label="t('settings.spotifyMirrorSilent')"
                  />
                </SettingRow>
              </template>
            </SettingGroup>
          </template>

          <!-- Library -->
          <template v-else-if="section === 'library'">
            <SettingGroup :title="t('settings.libraryGroup')">
              <SettingRow
                :label="t('settings.coverCache')"
                :description="t('settings.coverCacheHint')"
              >
                <UiSwitch
                  v-model="s.cache_cover_art"
                  :aria-label="t('settings.coverCache')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.reconcile')"
                :description="t('settings.reconcileHint')"
                stacked
              >
                <UiButton
                  variant="secondary"
                  icon="wand"
                  :loading="reconciling"
                  @click="reconcile"
                >
                  {{ t('settings.reconcileButton') }}
                </UiButton>
                <p
                  v-if="reconcileResult"
                  class="text-[13px]"
                  :class="reconcileFailed ? 'text-danger' : 'text-accent'"
                >
                  {{ reconcileResult }}
                </p>
              </SettingRow>
            </SettingGroup>
            <ExternalLibrarySettings />
          </template>

          <!-- Apps: pairing, sign-in, the server's name -->
          <template v-else-if="section === 'users'">
            <UsersSettings />
          </template>

          <template v-else-if="section === 'activity'">
            <ActivitySettings />
          </template>

          <template v-else-if="section === 'server'">
            <SettingGroup
              :title="t('settings.networkGroup')"
              :description="t('settings.networkHint')"
            >
              <ServerPortSetting />
            </SettingGroup>
          </template>

          <template v-else-if="section === 'apps'">
            <AppsSettings />
          </template>

          <!-- About -->
          <template v-else-if="section === 'about'">
            <div
              class="flex items-center gap-4 rounded-panel border border-line-2 bg-surface p-6"
            >
              <AppLogo :size="56" />
              <div class="min-w-0">
                <p class="text-display text-2xl font-bold">Downtify</p>
                <p class="tabular text-sm text-muted">
                  {{ t('settings.version', { version: version || '—' }) }}
                </p>
              </div>
              <UiButton
                v-if="update?.update_available"
                variant="primary"
                icon="sparkle"
                class="ml-auto"
                :href="update.release_url"
              >
                {{
                  t('nav.updateAvailable', { version: update.latest_version })
                }}
              </UiButton>
              <UiBadge
                v-else-if="update"
                tone="accent"
                icon="check"
                class="ml-auto"
              >
                {{ t('settings.upToDate') }}
              </UiBadge>
            </div>
            <SettingGroup>
              <SettingRow
                :label="t('settings.source')"
                :description="t('settings.sourceHint')"
              >
                <UiButton
                  variant="ghost"
                  icon="arrow-up-right"
                  href="https://github.com/henriquesebastiao/downtify"
                >
                  GitHub
                </UiButton>
              </SettingRow>
              <SettingRow
                :label="t('settings.docs')"
                :description="t('settings.docsHint')"
              >
                <UiButton
                  variant="ghost"
                  icon="arrow-up-right"
                  href="https://henriquesebastiao.github.io/downtify/"
                >
                  {{ t('settings.openDocs') }}
                </UiButton>
              </SettingRow>
            </SettingGroup>
          </template>
        </div>
      </Transition>
    </div>

    <!-- Save bar -->
    <Transition name="now-playing">
      <div
        v-if="sm.dirty.value || sm.saveErrorText.value"
        class="sticky z-30 mx-auto flex w-full max-w-2xl flex-wrap items-center gap-3 rounded-panel border border-line-3 bg-surface-2/95 py-3 pr-3 pl-5 shadow-float backdrop-blur-xl"
        :class="
          hasTrack
            ? 'bottom-[calc(10rem+env(safe-area-inset-bottom))] md:bottom-28'
            : 'bottom-[calc(5.75rem+env(safe-area-inset-bottom))] md:bottom-6'
        "
        role="status"
      >
        <p
          class="min-w-0 flex-1 text-sm"
          :class="sm.saveErrorText.value ? 'text-danger' : 'text-fg-2'"
        >
          {{ sm.saveErrorText.value || t('settings.unsaved') }}
        </p>
        <UiButton
          variant="plain"
          :disabled="sm.saving.value"
          @click="discard"
          >{{ t('settings.discard') }}</UiButton
        >
        <UiButton
          variant="primary"
          icon="check"
          :loading="sm.saving.value"
          @click="save"
        >
          {{ t('settings.save') }}
        </UiButton>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import AppLogo from '/src/components/ui/AppLogo.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import ExperimentalBadge from '/src/components/ui/ExperimentalBadge.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import CookiesCard from '/src/components/settings/CookiesCard.vue'
import ConnectionTest from '/src/components/settings/ConnectionTest.vue'
import ExternalLibrarySettings from '/src/components/settings/ExternalLibrarySettings.vue'
import PathSuggestInput from '/src/components/settings/PathSuggestInput.vue'
import PresetPicker from '/src/components/settings/PresetPicker.vue'
import AccountSettings from '/src/components/settings/AccountSettings.vue'
import ActivitySettings from '/src/components/settings/ActivitySettings.vue'
import AppsSettings from '/src/components/settings/AppsSettings.vue'
import ServerPortSetting from '/src/components/settings/ServerPortSetting.vue'
import UsersSettings from '/src/components/settings/UsersSettings.vue'
import SettingGroup from '/src/components/settings/SettingGroup.vue'
import SettingRow from '/src/components/settings/SettingRow.vue'
import SourceOrder from '/src/components/settings/SourceOrder.vue'
import LyricsOrder from '/src/components/settings/LyricsOrder.vue'
import API from '/src/model/api'
import {
  clampCoverResolution,
  clampDownloadDelaySeconds,
  clampExternalSyncDelaySeconds,
  clampParallelDownloads,
  useSettingsManager,
} from '/src/model/settings'
import { usePlayer } from '/src/model/player'
import { useAccount } from '/src/model/account'
import { useAuth } from '/src/model/auth'
import { settingsSectionsFor } from '/src/lib/auth'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useTheme } from '/src/model/theme'
import { useUi } from '/src/model/ui'
import { useUpdateCheck } from '/src/model/updateCheck'
import { useI18n } from '/src/i18n'

const { t, locale, setLocale, locales } = useI18n()
const route = useRoute()
const sm = useSettingsManager()
const auth = useAuth()
const account = useAccount()
const theme = useTheme()
const { showLyrics } = usePlayerPrefs()
const ui = useUi()
const player = usePlayer()
const update = useUpdateCheck().status

const hasTrack = computed(() => !!player.currentTrack.value)
const s = sm.settings
const version = localStorage.getItem('version')

// Telegram test: sends the notifications block as it stands in the form,
// saved or not, so a token/chat id can be checked before saving.
const notificationTest = ref('')
async function sendTestNotification() {
  notificationTest.value = 'sending'
  try {
    const res = await API.testNotifications(s.value.notifications)
    notificationTest.value = res?.data?.ok ? 'sent' : 'failed'
  } catch {
    notificationTest.value = 'failed'
  }
}

// last.fm scrobbling: the Connect flow asks for a request token, the user
// approves on last.fm, then the token is traded for a session key that the
// form saves. The test button checks a saved session without saving.
const lastfmAuth = ref({ token: '', url: '', busy: false })
const scrobblingTest = ref('')

async function startLastfmAuth() {
  scrobblingTest.value = ''
  lastfmAuth.value = { token: '', url: '', busy: true }
  try {
    const res = await API.startLastfmAuth({
      lastfm_api_key: s.value.scrobbling.lastfm_api_key,
      lastfm_api_secret: s.value.scrobbling.lastfm_api_secret,
    })
    const data = res?.data || {}
    if (data.ok && data.token) {
      lastfmAuth.value = {
        token: data.token,
        url: data.auth_url,
        busy: false,
      }
    } else {
      lastfmAuth.value = { token: '', url: '', busy: false }
      scrobblingTest.value = 'failed'
    }
  } catch {
    lastfmAuth.value = { token: '', url: '', busy: false }
    scrobblingTest.value = 'failed'
  }
}

async function finishLastfmAuth() {
  lastfmAuth.value = { ...lastfmAuth.value, busy: true }
  try {
    const res = await API.finishLastfmAuth({
      lastfm_api_key: s.value.scrobbling.lastfm_api_key,
      lastfm_api_secret: s.value.scrobbling.lastfm_api_secret,
      token: lastfmAuth.value.token,
    })
    const data = res?.data || {}
    if (data.ok && data.session_key) {
      s.value.scrobbling.lastfm_session_key = data.session_key
      s.value.scrobbling.lastfm_username = data.username || ''
      lastfmAuth.value = { token: '', url: '', busy: false }
      scrobblingTest.value = 'ok'
    } else {
      lastfmAuth.value = { ...lastfmAuth.value, busy: false }
      scrobblingTest.value = 'failed'
    }
  } catch {
    lastfmAuth.value = { ...lastfmAuth.value, busy: false }
    scrobblingTest.value = 'failed'
  }
}

async function runScrobblingTest() {
  scrobblingTest.value = 'testing'
  try {
    const res = await API.testScrobbling(s.value.scrobbling)
    scrobblingTest.value = res?.data?.ok ? 'ok' : 'failed'
  } catch {
    scrobblingTest.value = 'failed'
  }
}

function disconnectLastfm() {
  s.value.scrobbling.lastfm_session_key = ''
  s.value.scrobbling.lastfm_username = ''
  lastfmAuth.value = { token: '', url: '', busy: false }
  scrobblingTest.value = ''
}

// Spotify Mirror: plays in Downtify start the same track on the user's
// own Spotify Connect device (this fork ships a silent one on the
// server), so the listening shows up on Spotify. The connect flow saves
// the block first - Spotify reads the saved client id - then sends the
// browser to Spotify, which returns through the callback into this
// page.
const spotifyDevices = ref([])
const spotifyDevicesLoading = ref(false)
const spotifyConnecting = ref(false)
const spotifyTest = ref('')
const spotifyTestResult = ref(null)

async function loadSpotifyDevices() {
  spotifyDevicesLoading.value = true
  try {
    const res = await API.spotifyMirrorDevices()
    const devices = res?.data?.devices || []
    spotifyDevices.value = devices.map((d) => ({
      value: d.id,
      label: d.name,
    }))
    if (!spotifyDevices.value.length) {
      ui.toast(t('settings.spotifyMirrorNoDevices'), { kind: 'error' })
    }
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    spotifyDevicesLoading.value = false
  }
}

async function connectSpotify() {
  if (spotifyConnecting.value) return
  spotifyConnecting.value = true
  try {
    if (await sm.saveSettings()) {
      window.location.assign('/integrations/spotify/authorize')
    }
  } finally {
    spotifyConnecting.value = false
  }
}

async function runSpotifyMirrorTest() {
  spotifyTest.value = 'testing'
  try {
    const res = await API.testSpotifyMirror(s.value.spotify_mirror)
    const data = res?.data || {}
    if (data.ok) {
      spotifyTest.value = 'ok'
      spotifyTestResult.value = data
    } else {
      spotifyTest.value = 'failed'
    }
  } catch {
    spotifyTest.value = 'failed'
  }
}

const spotifyMirrorOkLabel = computed(() => {
  const r = spotifyTestResult.value
  if (!r) return t('settings.spotifyMirrorConnected')
  return t('settings.spotifyMirrorOk', {
    username: r.username ?? '',
    device: r.device ?? '',
  })
})

// Connected (refresh token from the callback flow present) disables the
// connect button: reconnect only makes sense after a disconnect.
const spotifyConnected = computed(() => !!s.value.spotify_mirror.refresh_token)

// The callback lands on /settings/apps with a result flag.
onMounted(() => {
  const flag = route.query.spotify
  if (flag === 'connected') {
    ui.toast(t('settings.spotifyMirrorConnected'))
  } else if (flag === 'error') {
    ui.toast(t('settings.spotifyMirrorError'), { kind: 'error' })
  }
})

// Storage: how full the disk is and which songs sit on it twice. The
// report loads on section open; deleting drops the library cache server
// side and re-loads the report.
const storage = ref({
  disk: { total: 0, used: 0, free: 0, percent: 0 },
  library: { bytes: 0, tracks: 0 },
  duplicates: { groups: [], total_wasted_bytes: 0 },
})
const storageLoading = ref(false)
const storageDeleting = ref(false)
const storageMessage = ref('')
const storageMessageOk = ref(false)
const storageLoaded = ref(false)

function formatBytes(bytes) {
  const value = Number(bytes) || 0
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  const digits = size >= 100 || unit === 0 ? 0 : 1
  return `${size.toFixed(digits)} ${units[unit]}`
}

async function loadStorage() {
  storageLoading.value = true
  storageMessage.value = ''
  try {
    const [report, duplicates] = await Promise.all([
      API.storageReport(),
      API.storageDuplicates(),
    ])
    const r = report?.data || {}
    const d = duplicates?.data || {}
    storage.value = {
      disk: r.disk || storage.value.disk,
      library: r.library || storage.value.library,
      duplicates: d.groups ? d : storage.value.duplicates,
    }
    storageLoaded.value = true
  } catch {
    storageMessage.value = t('settings.storageFailed')
    storageMessageOk.value = false
  } finally {
    storageLoading.value = false
  }
}

async function deleteDuplicates() {
  storageDeleting.value = true
  storageMessage.value = ''
  try {
    const files = storage.value.duplicates.groups.flatMap((group) =>
      group.duplicates.map((dup) => dup.file)
    )
    const res = await API.deleteStorageDuplicates(files)
    const removed = res?.data?.removed || 0
    storageMessage.value = t('settings.deleted', { count: removed })
    storageMessageOk.value = true
    await loadStorage()
  } catch {
    storageMessage.value = t('settings.deleteFailed')
    storageMessageOk.value = false
  } finally {
    storageDeleting.value = false
  }
}

// Normal users see General, Apps and About; the rest is the server's,
// an admin's to change.
const sections = computed(() =>
  settingsSectionsFor(
    auth.user.value?.role,
    [
      { id: 'general', icon: 'sliders', label: t('settings.general') },
      {
        id: 'sources',
        icon: 'download',
        label: t('settings.sources'),
        admin: true,
      },
      { id: 'files', icon: 'folder', label: t('settings.files'), admin: true },
      { id: 'tags', icon: 'tag', label: t('settings.tags'), admin: true },
      { id: 'navidrome', icon: 'server', label: 'Navidrome', admin: true },
      {
        id: 'notifications',
        icon: 'bell',
        label: t('settings.notifications'),
        admin: true,
      },
      {
        id: 'scrobbling',
        icon: 'music',
        label: t('settings.scrobbling'),
        admin: true,
      },
      {
        id: 'spotify',
        icon: 'globe',
        label: t('settings.spotifyMirror'),
        admin: true,
      },
      {
        id: 'storage',
        icon: 'hard-drive',
        label: t('settings.storage'),
        admin: true,
      },
      {
        id: 'library',
        icon: 'library',
        label: t('settings.library'),
        admin: true,
      },
      {
        id: 'users',
        icon: 'users',
        label: t('settings.users'),
        admin: true,
        accounts: true,
      },
      {
        id: 'activity',
        icon: 'activity',
        label: t('settings.activity'),
        admin: true,
      },
      {
        id: 'server',
        icon: 'hard-drive',
        label: t('settings.server'),
        admin: true,
      },
      {
        id: 'apps',
        icon: 'monitor',
        label: t('settings.apps'),
        // The apps themselves are still being built (AppsSettings).
        experimental: true,
      },
      { id: 'about', icon: 'info', label: t('settings.about') },
    ],
    { authDisabled: auth.authDisabled.value }
  )
)

const section = computed(() => {
  const requested = String(route.params.section || '')
  return sections.value.some((item) => item.id === requested)
    ? requested
    : 'general'
})

// The storage report reads the whole library; load it when the section
// opens, and again when asked to refresh.
watch(section, (value) => {
  if (value === 'storage' && !storageLoaded.value && !storageLoading.value) {
    loadStorage()
  }
})

function needsValue(value) {
  return String(value ?? '').trim() ? '' : t('settings.required')
}

const templateTokens = [
  '{artists}',
  '{artist}',
  '{title}',
  '{album}',
  '{tracknumber}',
  '{year}',
  '/',
]

function addToken(token) {
  const current = String(s.value.output || sm.settingsOptions.output)
  const extIndex = current.lastIndexOf('.{output-ext}')
  const base = extIndex >= 0 ? current.slice(0, extIndex) : current
  const sep = token === '/' || base.endsWith('/') ? '' : ' - '
  s.value.output = `${base}${base ? sep : ''}${token}.{output-ext}`
}

const templatePreview = computed(() => {
  const template = String(s.value.output || sm.settingsOptions.output)
  const values = {
    '{artists}': 'Kenji Aoki, Mira Kovač',
    '{artist}': 'Kenji Aoki',
    '{title}': 'Harbor Lights',
    '{album}': 'Glass Harbor',
    '{tracknumber}': '01',
    '{year}': '2025',
    '{output-ext}': s.value.format || 'mp3',
  }
  return Object.entries(values).reduce(
    (text, [token, value]) => text.split(token).join(value),
    template
  )
})

async function save() {
  if (!String(s.value.output || '').trim())
    s.value.output = sm.settingsOptions.output
  const ok = await sm.saveSettings()
  if (ok) ui.toast(t('settings.saved'), { kind: 'success' })
}

function discard() {
  sm.reset()
  sm.saveErrorText.value = ''
}

function openShortcuts() {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: '?' }))
}

const reconciling = ref(false)
const reconcileResult = ref('')
const reconcileFailed = ref(false)

async function reconcile() {
  reconciling.value = true
  reconcileResult.value = ''
  reconcileFailed.value = false
  try {
    const { data } = await API.reconcileLibrary()
    const parts = []
    if (data.paths_updated)
      parts.push(t('settings.reconcilePaths', { count: data.paths_updated }))
    if (data.pruned_stale)
      parts.push(t('settings.reconcilePruned', { count: data.pruned_stale }))
    if (data.content_keys_backfilled) {
      parts.push(
        t('settings.reconcileIndexed', { count: data.content_keys_backfilled })
      )
    }
    const refreshed = data.playlists_affected || []
    if (refreshed.length && (data.refresh_m3u || data.refresh_navidrome)) {
      parts.push(
        t('settings.reconcilePlaylists', { playlists: refreshed.join(', ') })
      )
    }
    reconcileResult.value = parts.length
      ? parts.join(' ')
      : t('settings.reconcileNone')
  } catch {
    reconcileFailed.value = true
    reconcileResult.value = t('settings.reconcileError')
  } finally {
    reconciling.value = false
  }
}

onBeforeRouteLeave(async (to) => {
  if (!sm.dirty.value || to.name === 'Settings') return true
  const leave = await ui.confirm({
    title: t('settings.leaveTitle'),
    body: t('settings.leaveBody'),
    confirmLabel: t('settings.discard'),
    danger: true,
  })
  if (leave) sm.reset()
  return leave
})
</script>
