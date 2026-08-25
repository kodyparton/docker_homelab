# Second Brain — User Guide

Everything below is stuff you can do today in Discord, once the one-time setup (see the bottom of this guide) is done. For how it's built internally, see `architecture/second-brain.md` and `architecture/journaling.md` — this guide is just "how do I use it."

There is no command syntax to learn. Talk to it like a person. Type, or send a voice message — both work the same.

## The four things it does

### 1. Remember things

Just say it.

> the storage unit door code is 7734
>
> my sister's birthday is October 12th
>
> I decided to go with the Vikunja recommendation over Planka

No prefix needed. It figures out on its own that you're telling it something, not asking or chatting, and it'll confirm what it stored:

> Got it — I'll remember: "storage unit door code is 7734"

### 2. Ask about things

> what's the storage unit code?
>
> when's my sister's birthday?
>
> did I already decide on a task manager?

It searches everything it's been taught, and answers using only what it actually finds. If it doesn't know, it says so — it won't make something up to sound helpful.

It also remembers what you were just talking about *today*, so follow-ups work naturally:

> what's the guest wifi password?
> **it:** the guest wifi password is SunnyDay42
> what about the garage code?
> **it:** *(knows you're still asking about codes/passwords, answers in context)*

### 3. Tell it to forget something

> forget the storage unit code, it changed
>
> actually never mind about my sister's birthday thing

It searches for the closest match to what you described and deletes it — but only if it's confident it found the right thing. If it's not sure, it tells you nothing matched rather than guessing and deleting the wrong memory. It always tells you exactly what got removed.

### 4. Give it a task

> remind me to call the vet tomorrow
>
> I need to renew the car registration
>
> add a task to follow up with the contractor

This creates a real task in Vikunja (once that's connected — see setup), not just a memory. You'll get a confirmation with a checkmark.

### Just talk to it

Anything that isn't one of the above — a greeting, a reaction, small talk — gets a normal, warm reply instead of being forced through "search my memory for an answer." It's a conversation partner, not a search box.

## Photos and voice

**Send a photo** (with or without a caption) and it gets logged for the day — it'll confirm with a quick "📷 saved." It doesn't look at the image itself (no vision model yet), just the filename and whatever you captioned it with.

**Send a voice message** and it gets transcribed automatically, then handled exactly like you'd typed it — remember, ask, forget, task, or chat, whichever fits. No difference in what you can say.

## The daily rhythm (things it does without being asked)

- **9pm** — it posts 3 reflective questions in the channel. Reply to them like anything else; your reply becomes part of that night's journal.
- **11:45pm** — it writes a short, honest journal entry for the day, using everything you told it, any photos you sent, and (once connected) your Strava activities and Apple Health workouts for the day. Posted in Discord, saved in its own memory, and optionally saved as a dated note in Trilium.
- **8am** — if anything you've told it references a date or deadline coming up in the next 3 days, it gives you a heads-up without being asked.
- **Sundays, 6pm** — a "what I learned about you this week" recap.

You don't do anything for these — they just happen. Reply to the evening prompts if you want them to count for that day's journal; ignore them if you don't feel like it.

## Things worth knowing

- **It only knows what you've told it, plus this entire homelab's documentation and your Obsidian vault** — every service/port/known issue, and everything in `~/Obsidian/KodyBrain` (your other second brain's `SOUL.md`/`USER.md`/`MEMORY.md`/`HABITS.md`/daily notes), both refreshed automatically every morning. Ask it "why does the mount keep breaking on sonarr" or "what are my habit pillars" and it answers from the real source either way. This is read-only — nothing this bot does ever writes back into your Obsidian vault.
- **Replies take a few seconds to ~30 seconds.** It's running entirely on this Mac, not a cloud API — there's real thinking happening, not instant lookup. It shows "typing..." the whole time.
- **Nothing leaves this machine.** No external AI API, no cloud service sees what you tell it.
- **Old conversations get quietly tidied up.** Once a chat exchange is over a month old, it gets summarized into one condensed memory instead of kept verbatim forever — keeps things fast and relevant without losing the substance.
- **Want to see everything it knows, all at once?** Run `python3 scripts/export_second_brain.py` in the repo — dumps everything to a markdown file you can read top to bottom.
- **Want to feed it something else big at once** (old notes, a braindump, another folder) instead of typing facts one at a time? `python3 scripts/seed_second_brain.py <file-or-folder>`. Your Obsidian vault is already covered automatically, no need to run this for that.

## One-time setup checklist

If any of this isn't done yet, that feature just won't work until it is — everything else keeps working fine. Full details for each item are in `architecture/second-brain.md` and `architecture/journaling.md`.

| Feature | What's needed |
|---|---|
| Talking to it at all | A dedicated Discord bot (token + channel ID) in `brain-bot/.env`, then `docker compose up -d --build` in `brain-bot/`, then activate workflow 18 in n8n |
| Evening prompts, journal, reminders, weekly digest | The same bot token pasted into n8n's "Second Brain Discord Bot" credential (as `Bot YOUR_TOKEN`), channel ID filled into workflows 19/20/24/25, all four activated |
| Voice messages | Nothing — already running |
| Task creation | Vikunja account + API token → n8n's "Vikunja API Token" credential, project ID → workflow 18's "Create Vikunja Task" node |
| Strava in the journal | Strava API app → n8n's "Strava API" credential → click Connect |
| Apple Health in the journal | "Health Auto Export" iOS app → automation posting to `https://n8n.kodyparton.com/webhook/apple-health-import` |
| Journal saved to Trilium | Trilium ETAPI token → n8n credential, parent note ID → workflow 20 |

Everything in that table is designed to fail gracefully if skipped — a missing Strava connection just means no Strava data in that day's journal, not a broken journal.
