import os
import logging

import aiohttp
import discord

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("brain-bot")

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
N8N_WEBHOOK_URL = os.environ["N8N_WEBHOOK_URL"]
# Comma-separated list of channel IDs the bot will respond in. If empty,
# the bot only responds to DMs.
_raw_channel_ids = [c.strip() for c in os.environ.get("DISCORD_CHANNEL_IDS", "").split(",") if c.strip()]
ALLOWED_CHANNEL_IDS = set()
for _c in _raw_channel_ids:
    if _c.isdigit():
        ALLOWED_CHANNEL_IDS.add(int(_c))
    else:
        log.warning("Ignoring non-numeric DISCORD_CHANNEL_IDS entry: %r", _c)
if not ALLOWED_CHANNEL_IDS:
    log.warning("No valid DISCORD_CHANNEL_IDS configured — bot will only respond to DMs.")
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "120"))

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    log.info("Logged in as %s (id=%s)", client.user, client.user.id)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    if not is_dm and message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    content = message.content.strip()
    images = [
        {"url": a.url, "filename": a.filename, "content_type": a.content_type}
        for a in message.attachments
        if (a.content_type or "").startswith("image/")
    ]
    if not content and not images:
        return

    async with message.channel.typing():
        payload = {
            "content": content,
            "images": images,
            "author_id": str(message.author.id),
            "author_name": str(message.author),
            "channel_id": str(message.channel.id),
            "is_dm": is_dm,
        }
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(N8N_WEBHOOK_URL, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        log.error("n8n returned %s: %s", resp.status, body[:500])
                        await message.reply(
                            "Something went wrong reaching my brain (n8n returned "
                            f"{resp.status}). Check the workflow's execution log."
                        )
                        return
                    data = await resp.json(content_type=None)
        except Exception:
            log.exception("Failed to reach n8n webhook")
            await message.reply(
                "Couldn't reach my brain at all (n8n unreachable or timed out). "
                "Check that the `Second Brain - Chat` workflow is active."
            )
            return

    reply_text = (data or {}).get("reply") or "(n8n returned no reply text)"
    # Discord hard-caps messages at 2000 chars; split long replies.
    for i in range(0, len(reply_text), 1900):
        await message.reply(reply_text[i : i + 1900])


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
