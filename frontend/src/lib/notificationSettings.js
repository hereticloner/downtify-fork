export const NOTIFICATION_EVENTS = [
  'watch.downloaded',
  'download.completed',
  'download.failed',
  'download.batch',
  'upgrade.started',
  'upgrade.finished',
  'upgrade.failed',
  'backup.completed',
  'backup.failed',
]

const CHANNEL_FIELDS = {
  telegram: ['bot_token', 'chat_id'],
  ntfy: ['url', 'token'],
  webhook: ['url', 'token'],
}

export function blankNotificationSettings() {
  return {
    enabled: false,
    events: ['watch.downloaded'],
    channels: {
      telegram: {
        enabled: false,
        events: ['watch.downloaded'],
        bot_token: '',
        chat_id: '',
        bot_token_set: false,
        chat_id_set: false,
      },
      ntfy: {
        enabled: false,
        events: [],
        url: '',
        token: '',
        url_set: false,
        token_set: false,
      },
      webhook: {
        enabled: false,
        events: [],
        url: '',
        token: '',
        url_set: false,
        token_set: false,
      },
    },
  }
}

export function mergeNotificationSettings(saved = {}) {
  const base = blankNotificationSettings()
  const channels = saved.channels || {}
  for (const [name, fields] of Object.entries(CHANNEL_FIELDS)) {
    const incoming = channels[name] || {}
    base.channels[name] = {
      ...base.channels[name],
      ...incoming,
      events: Array.isArray(incoming.events)
        ? incoming.events.filter((event) => NOTIFICATION_EVENTS.includes(event))
        : base.channels[name].events,
    }
    for (const field of fields) {
      if (typeof base.channels[name][field] !== 'string') {
        base.channels[name][field] = ''
      }
    }
  }
  base.enabled = Boolean(saved.enabled)
  base.events = Array.isArray(saved.events)
    ? saved.events.filter((event) => NOTIFICATION_EVENTS.includes(event))
    : base.events
  return base
}

export function notificationTestRequest(config, channel) {
  return { channel, config }
}
