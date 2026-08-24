# Brain Bot

Custom Discord relay — the only piece of this stack that's original application code rather than an off-the-shelf image. A thin, stateless bridge: reads Discord messages, forwards them to n8n, sends back whatever n8n replies with. All the actual intelligence (RAG, memory, generation) lives in n8n/Ollama/Qdrant — this bot does no thinking of its own.

## Quick Facts

| | |
|---|---|
| **Image** | built locally from `brain-bot/Dockerfile` (`python:3.12-slim` + `discord.py`) |
| **Container name** | `brain-bot` |
| **Compose file** | `brain-bot/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | none — outbound only (Discord Gateway websocket out, HTTP to n8n out) |
| **Local URL** | n/a |
| **Public URL** | n/a |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

None — fully stateless. `bot.py` is baked into the image at build time.

## Dependencies

- **Depends on:** Discord's Gateway API (real-time connection, not a webhook), n8n's `second-brain-chat` webhook (`http://192.168.178.69:5678/webhook/second-brain-chat`), and [`whisper`](whisper.md) for voice message transcription (audio attachments get downloaded and transcribed before the text ever reaches n8n).
- **Depended on by:** nothing — it's the entry point.

## Credentials & Secrets

`brain-bot/.env` (gitignored) holds `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_IDS`, and `WHISPER_URL` (defaults to the local whisper container, rarely needs changing). **This is a dedicated bot application, separate from the personal-assistant Discord bot** that Kody's Obsidian-based second brain already uses (see `USER.md`'s `Discord Bot Token` entry) — deliberately not shared, to keep the two systems' failure modes and permissions independent. `.env.example` is the committed placeholder template.

**This same bot token is also needed by n8n's `Second Brain Discord Bot` credential** (used by workflows 19, 20, 24, 25 to post messages the bot didn't directly trigger — prompts, journal entries, reminders, digests) — one Discord application, two places its token needs to be pasted.

## External Access

n/a — connects outward only, nothing listens for inbound connections.

## Backups

n/a — stateless, `bot.py` is version-controlled.

## Automation

Is itself the trigger for **18 - Second Brain - Chat** — every non-bot message in an allow-listed channel (or any DM) gets POSTed to that workflow, and whatever JSON `{"reply": "..."}` comes back gets sent to Discord, split across multiple messages if over Discord's 2000-character limit.

## Known Issues / Gotchas

- **Requires the "Message Content Intent"** enabled on the Discord bot application (Developer Portal → Bot tab) — without it, `message.content` arrives empty and the bot can't see what anyone actually typed.
- Response latency is bounded by Ollama inference time on this hardware (M1, 16GB) — expect several seconds to ~30s per reply depending on question complexity, longer for voice messages (transcription happens first). The bot shows a "typing..." indicator the whole time so it doesn't look hung.
- Voice messages: any attachment with an `audio/*` content type gets transcribed and treated as if it were typed. If transcription fails, the bot says so explicitly rather than silently ignoring the message.
- If n8n's `second-brain-chat` workflow isn't active, or Ollama/Qdrant aren't running, the bot replies with an explicit error message rather than staying silent — check `docker logs brain-bot` first if Discord ever really does go quiet.

## Change Log

- `2026-08-24` — Built.
