import { describe, expect, it } from 'vitest'
import {
  blankNotificationSettings,
  mergeNotificationSettings,
  notificationTestRequest,
} from '../lib/notificationSettings'

describe('notification settings form', () => {
  it('starts with every channel off and no secret values', () => {
    const value = blankNotificationSettings()
    expect(value.enabled).toBe(false)
    expect(Object.keys(value.channels)).toEqual(['telegram', 'ntfy', 'webhook'])
    expect(value.channels.telegram.bot_token).toBe('')
    expect(value.channels.telegram.bot_token_set).toBe(false)
  })

  it('merges saved flags without inventing secret values', () => {
    const value = mergeNotificationSettings({
      enabled: true,
      channels: {
        telegram: { enabled: true, bot_token_set: true, chat_id_set: true },
      },
    })
    expect(value.channels.telegram).toMatchObject({
      enabled: true,
      bot_token_set: true,
      chat_id_set: true,
      bot_token: '',
      chat_id: '',
    })
    expect(value.channels.ntfy.enabled).toBe(false)
  })

  it('builds a channel-specific test request', () => {
    expect(notificationTestRequest({ enabled: true }, 'ntfy')).toEqual({
      channel: 'ntfy',
      config: { enabled: true },
    })
  })
})
