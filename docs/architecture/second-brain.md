# Second Brain

A self-hosted, Discord-native knowledge assistant: chat with it to ask questions grounded in facts it's been taught, and teach it new facts the same way. Fully local — no external API calls, no per-message cost, nothing leaves this Mac.

This is a **separate system** from Kody's existing Obsidian-based second brain (the `SOUL.md`/`USER.md`/`MEMORY.md`/daily-notes system that Claude Code itself operates as, with its own Discord bot). The two are deliberately not merged — different bot application, different credentials, different failure domain. This one is homelab infrastructure, versioned and documented like everything else in this repo; the Obsidian one is a personal daily-driver assistant. They can absolutely be pointed at each other later (e.g., feed the Obsidian vault into this one's memory) but that's an opt-in step, not automatic.

## How it works

```mermaid
sequenceDiagram
    participant You as You (Discord)
    participant Bot as brain-bot
    participant n8n as n8n workflow 18
    participant Ollama
    participant Qdrant

    You->>Bot: "my car's oil change is due in March"
    Bot->>n8n: POST /webhook/second-brain-chat
    n8n->>Ollama: classify intent (store/forget/question/chat)
    Ollama-->>n8n: {"intent":"store","content":"..."}
    n8n->>Ollama: embed the fact
    Ollama-->>n8n: vector
    n8n->>Qdrant: upsert {text, vector}
    n8n-->>Bot: {"reply": "Got it, I'll remember..."}
    Bot-->>You: reply

    You->>Bot: "when's my car's oil change due?"
    Bot->>n8n: POST /webhook/second-brain-chat
    n8n->>Ollama: classify intent
    Ollama-->>n8n: {"intent":"question","content":"..."}
    n8n->>Ollama: embed the question
    Ollama-->>n8n: vector
    n8n->>Qdrant: search top 5 similar + today's conversation history
    Qdrant-->>n8n: matching facts + recent context
    n8n->>Ollama: generate answer, grounded in those facts
    Ollama-->>n8n: answer text
    n8n-->>Bot: {"reply": "..."}
    Bot-->>You: reply
```

There's no required syntax — no `remember:`, no `forget:`, no command prefixes. Every message goes through an LLM classification step first that figures out what you actually mean (store a fact, forget one, ask a question, or just chat) from natural phrasing, then routes accordingly. This was a deliberate redesign (2026-08-24) away from an earlier keyword-prefix version specifically to make it feel like a conversation rather than a command line.

Four services, each documented individually:

| Service | Role |
|---|---|
| [`brain-bot`](../containers/brain-bot.md) | Discord relay — the only custom code in this stack |
| [`n8n`](../containers/n8n.md) workflow **18 - Second Brain - Chat** | Orchestration — routes ingest vs. query, calls Ollama and Qdrant |
| [`ollama`](../containers/ollama.md) | Local LLM — embeddings (`nomic-embed-text`) and chat generation (`qwen2.5:7b-instruct`) |
| [`qdrant`](../containers/qdrant.md) | Vector memory — every fact it's been taught |

## Teaching it something

Just say it naturally, no prefix needed:

> the guest wifi password is on the fridge whiteboard

An LLM classification pass (a small, fast Ollama call before the "real" processing) recognizes this as something to remember, cleans it up, embeds it, stores it in Qdrant, and confirms. `remember: ...` / `note: ...` / `save: ...` still work fine if that's how it feels natural to phrase it — the classifier isn't confused by them — but nothing requires that syntax anymore.

## Asking it something

Just ask normally:

> what's the guest wifi password?

It embeds the question, retrieves the 5 most semantically similar stored facts (only ones scoring above a relevance threshold — see `qdrant.md`) *and* the last few things said today for continuity, and asks the local LLM to answer using that context. If nothing relevant was stored, it says so rather than guessing — this was deliberately tested to confirm it doesn't hallucinate an answer when the context is empty.

## Forgetting something

Also natural language, no special syntax:

> actually forget what I said about the wifi password

The classifier extracts what you want forgotten, semantically searches for the closest matching stored fact(s) (requiring a high confidence score — 0.6+ — so it doesn't delete the wrong thing on a vague description), deletes any matches, and tells you exactly what got removed. If nothing matched confidently enough, it says so and deletes nothing rather than guessing.

## Just talking to it

Anything that isn't a fact, a question, or a forget request — greetings, reactions, small talk — gets a normal conversational reply instead of being forced through the "answer from stored facts" machinery. It still has access to the last few exchanges from today for continuity (e.g. "haha yeah" after a previous exchange makes sense to it), it just isn't required to ground the reply in retrieved memory the way a real question is.

## Sending it a photo

Any image attachment (with or without a caption) gets logged rather than answered — the bot confirms with a short "📷 saved" reply. It doesn't analyze the image itself (no vision model in the loop), just the filename and whatever caption you included. This exists primarily to feed the daily journal — see `docs/architecture/journaling.md`.

Every exchange through this bot — facts, questions, chat, photos — also gets logged with today's date, which is what makes the [daily journaling system](journaling.md) possible, and what gives it same-day conversational memory.

## Setting the foundation of knowledge

An empty brain isn't useful. Two ways to seed it:

**1. Bulk-load from files** (recommended for the initial foundation):

```bash
python3 scripts/seed_second_brain.py <file-or-directory>
```

Accepts `.md`/`.txt` files, chunks them on blank lines (paragraph-level, so retrieval points to specific facts rather than whole documents), embeds and stores each chunk. Safe to re-run — content-hashed IDs mean re-running on unchanged files doesn't duplicate entries.

**Already done, and kept fresh automatically**: the entire homelab documentation set (every container doc + architecture map) is in its memory. **Workflow 22 - Refresh Homelab Knowledge** re-runs this seed against `docs/` every morning at 06:00 — the script deletes-then-reinserts each file's chunks by source path, so edits to a doc replace the stale version rather than piling up duplicates, and new docs get picked up automatically. Ask it things like "what port is sonarr on" or "why does the mount keep breaking" and it answers grounded in the same docs a human would read, updated daily.

**2. Point it at more of your life, if you want to.** The script works on any markdown/text — the Obsidian vault (`~/Obsidian/KodyBrain`), old notes, a braindump file, anything. This is a deliberate choice to leave to you rather than something done automatically: run `python3 scripts/seed_second_brain.py ~/Obsidian/KodyBrain` yourself whenever you want that content queryable here too. Nothing about this stack reaches into that vault on its own.

**3. Ongoing, the natural way** — just keep saying `remember: ...` in Discord as things come up. That's the intended steady-state, not a one-time chore.

## Setup steps you need to perform

Everything above is built and running except the one piece that fundamentally requires your own Discord account:

1. **Create a dedicated Discord bot application** (separate from any existing bot):
   - discord.com/developers/applications → New Application → name it whatever you like (e.g. "Homelab Brain").
   - Bot tab → Reset Token → copy it. Under **Privileged Gateway Intents**, enable **Message Content Intent** (required — without it the bot can't read message text).
   - OAuth2 → URL Generator → scope `bot`, permissions `Send Messages` + `Read Message History` + `View Channel` → open the generated URL, invite it to your server.
2. **Get the channel ID** you want it to listen in: Discord → User Settings → Advanced → enable Developer Mode → right-click the channel → Copy Channel ID. (DMs to the bot work regardless of this setting.)
3. **Fill in `brain-bot/.env`** (copy from `brain-bot/.env.example` if it doesn't exist yet): `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_IDS` (comma-separated if more than one channel).
4. **Start the bot**: `cd brain-bot && docker compose up -d --build`.
5. **Activate workflow 18** in n8n (`https://n8n.kodyparton.com` → find "18 - Second Brain - Chat" → toggle Active). n8n's API can create workflows but can't activate them — this one manual toggle is unavoidable, same as every other workflow in this stack.
6. Send it a message. If nothing happens, check `docker logs brain-bot` first (usually a bad token or the channel ID doesn't match), then n8n's execution log for workflow 18.

## What's already been built out (formerly "extending it later")

All four originally-deferred ideas from v1 are done as of 2026-08-24:

- ✅ **Multi-turn conversation memory** — question and chat replies both pull the last 4 exchanges from today's conversation log as context.
- ✅ **Backup coverage for Qdrant** — workflow 03 now triggers a fresh snapshot before each daily backup check, kept in `qdrant/snapshots/` (a separate bind mount from `qdrant/storage/`, gitignored), retains the last 3, and `scripts/backup_check.sh` verifies one exists and isn't stale.
- ✅ **A `forget` capability** — no longer keyword-gated (see "Forgetting something" above); natural language, confidence-thresholded.
- ✅ **Feeding it live homelab state** — workflow 22, daily 06:00.

## Extending it further

Ideas not yet built:

- **Vision-capable photo understanding** — currently photos are logged by filename/caption only, the LLM never looks at pixel content. Would need a vision model (e.g. `llava`, `qwen2.5vl`) — untested whether this hardware (M1, 16GB, already running one 7B model) can comfortably run two models loaded at once; worth a memory-usage test before committing to it.
- **Cross-channel/cross-user conversation isolation** — recent-history lookups currently filter by date only, not by Discord channel or author. Fine for a single-user bot in one channel (the deployed setup), but if `brain-bot` ever listens in multiple channels or multiple people talk to it, conversations would blend together. Would need `channel_id`/`author_id` added to the conversation log payload (they're already sent by the bot, just not stored yet) and filtered on.
- **Explicit fact correction** — right now updating a fact means forgetting the old one and stating the new one as two separate messages. A natural "actually it's X, not Y" in one message would need the classifier to support a fifth intent (`correct`) that does a search-and-replace in one step.
- **Feeding it the Obsidian vault** — still an explicit opt-in the user runs themselves (see above), not automated, by design.

## Brainstorm: further ideas (2026-08-24, not yet built)

- **Vikunja bridge** — the classifier already distinguishes intents; a fifth (`task`) could create a real Vikunja task via its API instead of just a Qdrant fact when you say something like "remind me to renew the car registration." Natural fit since both systems already exist in this repo.
- **Memory consolidation** — as conversation logs accumulate indefinitely, retrieval quality could degrade under volume. A periodic (weekly?) job that has the LLM review a day's or week's raw conversation entries and collapse them into a shorter summary point, keeping raw entries for a rolling window (e.g. 30 days) and summaries beyond that.
- **Proactive date-aware reminders** — scan stored facts for dates (appointments, deadlines) and have a daily job cross-reference against "today" or "this week," posting a heads-up rather than waiting to be asked.
- **Voice messages** — Discord supports voice messages; a local Whisper model (`whisper.cpp`, runs fine on CPU) could transcribe them into the same chat pipeline, so "talking" to the brain doesn't require typing.
- **Weekly "what I learned about you" digest** — same digest pattern already used elsewhere in this repo (see workflow 14), summarizing the week's stored facts and most-asked questions.
- **Full memory export** — a script that dumps every Qdrant point to a readable markdown file, the reverse of `seed_second_brain.py` — for backup, portability, or just browsing everything it knows outside of chat.
- **Correlating homelab state with journal mood** — it already knows both the known-issues log and daily journal entries; a query like "was I stressed the week the mount kept breaking" becomes answerable for free once both are in the same memory.
