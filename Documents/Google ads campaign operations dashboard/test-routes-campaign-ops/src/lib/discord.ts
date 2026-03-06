interface DiscordEmbed {
  title: string
  description?: string
  color?: number
  fields?: Array<{ name: string; value: string; inline?: boolean }>
  timestamp?: string
}

export async function sendDiscordNotification(
  content: string,
  embeds?: DiscordEmbed[]
): Promise<void> {
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL
  if (!webhookUrl) {
    console.log('[Discord] No webhook URL configured, skipping notification')
    console.log('[Discord] Message:', content)
    return
  }

  const body: Record<string, unknown> = { content }
  if (embeds) {
    body.embeds = embeds
  }

  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    console.error(`[Discord] Failed to send: ${response.status} ${response.statusText}`)
  }
}

export const DISCORD_COLOURS = {
  success: 0x22c55e,
  warning: 0xf59e0b,
  danger: 0xef4444,
  info: 0x3b82f6,
}
