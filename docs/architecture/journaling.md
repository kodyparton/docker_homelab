# Daily Journaling

Built on top of the [second brain](second-brain.md) — same bot, same Ollama, same Qdrant. Two new n8n workflows handle the daily rhythm, plus the chat workflow now quietly logs everything it sees so there's material to summarize.

## What happens automatically

**Every message through `brain-bot` now gets logged**, not just remembered facts. Workflow 18 (Second Brain - Chat) was extended with a third route:

| You send... | Route | What happens |
|---|---|---|
| An image (with or without caption) | **photo** | Logged to Qdrant as `type: photo` with the image's Discord CDN URL, filename, and caption — not downloaded/stored as a file anywhere, just referenced |
| `remember: ...` / `note: ...` / `save: ...` | **ingest** | Stored as a fact (`type: fact`, same as before) *and* logged as a conversation entry |
| Anything else (a question) | **query** | Answered via RAG as before, and the question+answer pair is logged (`type: conversation`) |

This logging is what makes the daily summary possible — without it, there'd be nothing to summarize beyond remembered facts.

**21:00 daily — [workflow 19] Daily Journal Prompt**: posts 3 randomly-picked reflective questions to Discord (rotates through a pool of 8). Reply to them like you'd reply to anyone — your reply gets logged the same as any other message and feeds into that night's summary.

**23:45 daily — [workflow 20] Daily Journal Summary**: pulls everything tagged with today's date —
- conversation log entries (`type: conversation`)
- photo entries (`type: photo`)
- Apple Health workouts, if any came in (`type: apple_health`)
- Strava activities for today, via a live API call (not from the log — pulled fresh)

— hands all of it to the local LLM with instructions to write a short, honest, first-person journal entry (explicitly told not to pad it out or invent details if the day was quiet). The result gets:
1. Stored in Qdrant as `type: journal` (so the brain itself can answer "what did I write about last Tuesday")
2. Posted to Discord
3. Attempted as a note in Trilium, titled with today's date (best-effort — see setup below)

## Setup steps you need to perform

Everything is built and deployed; these are the pieces that need your accounts/credentials.

### Required (for the journaling workflows to run at all)

Same as the second brain itself — the Discord bot from `docs/architecture/second-brain.md` needs to exist and be running. Workflows 19 and 20 use a **new credential**, `Second Brain Discord Bot` (n8n → Settings → Credentials), which needs the **same bot token** as `brain-bot/.env`'s `DISCORD_BOT_TOKEN` — paste it in as the `Authorization` header value in the form `Bot YOUR_TOKEN_HERE` (the word "Bot" and a space before the token, that's Discord's required header format). Also edit the "EDIT ME: Discord Channel ID" node in **both** workflow 19 and workflow 20 with your real channel ID.

Then activate workflows 19, 20, and 21 in n8n's UI (API can't activate, same limitation as everything else).

### Optional: Strava activities

1. Create a Strava API application: strava.com/settings/api → note the Client ID and Client Secret.
2. In n8n, open credential **"Strava API"** (OAuth2, already created as a stub) and fill in Client ID / Client Secret. Its Auth URL and Token URL are already set correctly (`strava.com/oauth/authorize` and `/oauth/token`).
3. Click **"Connect my account"** on that credential in the n8n UI — this runs the OAuth consent flow in a popup and gets you a refresh token, which n8n stores and auto-renews from then on. No manual token copying needed once the Client ID/Secret are in.
4. If this step is skipped, workflow 20 just quietly gets no Strava data for that day (the node has `continueOnFail` set) — the rest of the journal still generates normally.

### Optional: Apple Health

There's no official Apple Health API — the standard self-hosted workaround is the iOS app **"Health Auto Export – JSON+CSV"** (App Store, one-time or subscription purchase depending on features used), which can automate a daily export via an iOS Shortcut and POST it to a URL.

1. Install the app, grant it Health access.
2. Set up an automation (in the app or via iOS Shortcuts) to export workout data as JSON to: `https://n8n.kodyparton.com/webhook/apple-health-import` — run it daily, ideally before 23:45 so it's in before that day's journal summary runs.
3. **The field-name parsing in workflow 21 is best-effort** — I built it defensively against the JSON shape that app has historically used, but couldn't verify against a real export in this session. After your first real export, check n8n's execution log for workflow 21; if `Extract Workouts` produced 0 items from a real workout, open that node's code and adjust the field paths to match what actually arrived (the raw payload is right there in the execution log to compare against).

### Optional: Trilium journal notes

1. Log into Trilium (`http://192.168.178.69:8080`) — first-run setup if you haven't used it yet.
2. Options → ETAPI → Create new ETAPI token → copy it.
3. Create a note to serve as the journal's parent folder (e.g. "Journal"), note its Note ID (visible in Trilium's UI, or via the ETAPI itself).
4. In n8n, credential **"Trilium ETAPI"** → paste the token as the `Authorization` header value (just the raw token, no "Bot" prefix — Trilium's ETAPI expects the token directly).
5. Edit workflow 20's "EDIT ME: Discord Channel ID" node — it also holds `TRILIUM_JOURNAL_PARENT_NOTE_ID`, set that to the note ID from step 3.
6. If skipped, the Trilium step just fails silently (`continueOnFail`) and the journal still posts to Discord and saves in Qdrant either way.

## Known limitations

- **No dedup on Strava/Apple Health if the workflow runs twice in a day** — re-running workflow 20 manually would pull the same day's Strava activities again and generate a second journal entry. Not an issue for its normal once-daily schedule, just something to know if testing manually.
- **Photos aren't analyzed** — the LLM never actually looks at the image content, only the filename/caption you provide. Adding real image understanding would mean switching to a vision-capable Ollama model (e.g. `llava` or `qwen2.5vl`) for the photo-logging step specifically — a reasonable future enhancement, not done here (this hardware is already near its comfortable RAM ceiling with one 7B model loaded; a second vision model would need testing for whether both fit simultaneously).
- **The 21:00 prompt and 23:45 summary are independent** — if you reply to the 21:00 prompt after 23:45 (unlikely, but possible), that reply won't make it into that day's summary, since the summary only looks at Qdrant entries with today's date and by then it might be past midnight. Edge case, not fixed.
