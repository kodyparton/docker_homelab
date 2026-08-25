# n8n Automation Map

All workflows live in the `n8n` container (`https://n8n.kodyparton.com`). Every workflow is created **inactive** by default — n8n's public API cannot activate workflows, so each one is a deliberate manual toggle after its credentials are confirmed real. See each workflow's manual-setup steps (given when it was built) for exact credential requirements.

## Shared Credentials

| Credential name | Type | Used by |
|---|---|---|
| `Mac Mini SSH` | `sshPassword` | 01, 02, 03, 09, 10, 11, 17, 27 |
| `Homelab Discord Webhook` | `discordWebhookApi` | 01, 02, 03, 09, 10, 11, 12, 27, 29, 30 |
| `Sonarr API Key` / `Sonarr 4K API Key` | `httpHeaderAuth` | 14, 15 |
| `Radarr API Key` / `Radarr 4K API Key` | `httpHeaderAuth` | 14, 15 |
| `Prowlarr API Key` | `httpHeaderAuth` | 12 |
| `Overseerr API Key` | `httpHeaderAuth` | 13 |
| `Tautulli API Key` | `httpQueryAuth` | 14 |
| `Entra Graph (App-Only)` | `oAuth2Api` | 04a, 04b |
| `Job Pipeline Notion` | `notionApi` | 05 |
| `Earned It Discord Webhook` | `discordWebhookApi` | 16 (placeholder, not yet real) |
| `Second Brain Discord Bot` | `httpHeaderAuth` (`Authorization: Bot ...`) | 19, 20 (placeholder, needs the brain-bot's real token) |
| `Strava API` | `oAuth2Api` | 20 (placeholder, needs a real Strava app + OAuth connect) |
| `Trilium ETAPI` | `httpHeaderAuth` | 18, 20 (placeholder, needs a real ETAPI token — optional) |
| `Vikunja API Token` | `httpHeaderAuth` | 18 (connected 2026-08-25 — real token, project 1 "Inbox") |

Workflow 18 doesn't use n8n credential objects at all — Ollama and Qdrant have no authentication (both are LAN-only, deliberately never exposed publicly), so its HTTP Request nodes just call `http://192.168.178.69:11434` and `http://192.168.178.69:6333` directly.

## Workflow Registry

| # | Name | Trigger | Touches | Purpose |
|---|---|---|---|---|
| 01 | Certificate & Domain Expiry Monitor | daily 08:00 | TLS certs on 4 domains, RDAP | Alerts at 30/14/7 days to expiry |
| 02 | Docker Drift Detection | every 6h | every `compose.yml` + running containers | Alerts if a running image doesn't match what's declared |
| 03 | Backup Verification | daily | sonarr/radarr×2/prowlarr/tautulli/huntarr/lazylibrarian/audiobookshelf backup dirs | Alerts on missing/stale/corrupt backups |
| 04a | Entra Joiner | Form Trigger | Microsoft Graph API | Creates a user + assigns groups (needs a real Entra tenant, not yet set up) |
| 04b | Entra Leaver | Form Trigger | Microsoft Graph API | Revokes sessions, removes groups, disables account |
| 05 | Job Application Pipeline | every 6h | Adzuna API, Notion | Scores/dedupes NL job postings into Notion |
| 09 | Mount Health Self-Healer | every 15min | sonarr/sonarr-4k/radarr/radarr-4k/qbittorrent mounts | **Auto-restarts** containers with a dropped SMB mount |
| 10 | Storm Watch Snapshot | every 20min | NWS alerts API, local git | Local git commit (not push — see gotcha) on severe weather |
| 11 | Storage Runway Forecast | daily 07:00 | host disk space | Alerts if projected to run out within 21 days |
| 12 | Flaky Indexer Auto-Healer | every 6h | Prowlarr indexer stats | **Auto-disables** indexers with >50% failure rate |
| 13 | Smart Overseerr Triage | webhook (Overseerr) | TMDB watch/providers, Overseerr | **Auto-approves/declines** requests based on streaming availability |
| 14 | Weekly Media Server Digest | weekly Mon 08:00 | Tautulli, Sonarr×2, Radarr×2, qBittorrent | Posts a digest to Discord |
| 15 | Release Radar Digest | weekly Mon 08:00 | Sonarr×2, Radarr×2 calendars | Posts "this week's lineup" to Discord |
| 16 | Earned It (Strava-Gated Media Unlock) | webhook (Strava) | Strava, Overseerr | **Auto-approves** oldest pending request on a new weekly activity |
| 17 | Discord Ops Console | every 30s (poll) | Discord REST, SSH `docker ps` | Replies to `!status` in Discord with live container health |
| 18 | Second Brain - Chat | webhook (`brain-bot`) | Ollama, Qdrant, Vikunja, Trilium, Sonarr, Radarr, Tautulli | Conversational RAG: an LLM classification pass routes every message to one of 10 intents (store/forget/correct/question/chat/task/list_tasks/complete_task/note/media_query) — no required keywords. Unambiguous phrasing ("remember...", "forget...", "remind me to...") skips the classifier entirely via a regex fast-path, turning a ~2-3 minute round trip into ~1-4 seconds for `store`/`forget`/`task`/`list_tasks`. `correct` replaces a fact and stores its update in one message ("actually it's X, not Y") instead of a separate forget-then-store. `media_query` reads live Sonarr/Radarr/Tautulli data (not stored memory); `task`/`list_tasks`/`complete_task` read and write real Vikunja tasks; `note` writes to Trilium. Photos logged separately, voice messages transcribed by `whisper` before they ever reach this workflow. Every route writes a Qdrant entry, which feeds same-day conversational memory and the daily journal. Non-image messages first check a hash-keyed cache (`qa_cache` collection) before ever calling the classifier — an exact-repeat question gets an instant reply instead of another multi-minute LLM round trip. `forget`, `correct`, and `complete_task` snapshot what they're about to change into `shadow_log` before acting, so all three are recoverable. See `docs/architecture/second-brain.md`. |
| 27 | Second Brain Health Monitor | every 15min | Ollama, Qdrant, Whisper APIs; SSH `docker ps` | Alerts to Discord if any second-brain service is unreachable or its container isn't `Up` |
| 28 | Second Brain Self-Test | daily 05:00 | webhook `second-brain-chat` (calls workflow 18 directly) | Fires 6 canned messages through the safe-to-repeat intents (`chat`, `question`, a self-cleaning `store`+`forget` pair, `list_tasks`, `media_query`) and posts a pass/fail summary to Discord only when something fails or is too slow. Deliberately skips `task`/`complete_task`/`note` — those write real, non-idempotent data to Vikunja/Trilium. |
| 29 | Weekly Duplicate Fact Scan | weekly Sat 05:00 | Qdrant (vector search only, no LLM) | Finds pairs of stored facts whose embeddings are near-identical (≥92% similarity) and posts them to Discord for manual review — report-only, never auto-merges or deletes |
| 30 | Weekly Shadow Log Review | weekly Sun 19:00 | Qdrant (`shadow_log`) | Digests the week's `forget`/`complete_task` actions to Discord as an audit trail, and prunes `shadow_log` entries older than 90 days |
| 19 | Daily Journal Prompt | daily 21:00 | Discord (bot API) | Posts 3 rotating reflective prompts to Discord |
| 20 | Daily Journal Summary | daily 23:45 | Qdrant, Strava API, Ollama, Trilium (optional), Discord | Generates and posts a first-person journal entry from the day's logged conversations/photos/Strava/Apple Health data. See `docs/architecture/journaling.md`. |
| 21 | Apple Health Import | webhook (Health Auto Export app) | Qdrant | Receives daily workout export from iOS, logs each workout for the journal to use |
| 22 | Refresh Homelab Knowledge | daily 06:00 | SSH, `scripts/seed_second_brain.py` | Re-seeds `docs/` into Qdrant (delete-by-source then re-insert) so the brain's homelab knowledge doesn't go stale |
| 23 | Weekly Memory Consolidation | weekly Sun 04:00 | Qdrant, Ollama | Summarizes conversation entries older than 30 days into one point, deletes the originals |
| 24 | Proactive Reminders | daily 08:00 | Qdrant, Ollama, Discord | Scans stored facts for anything date-relevant to today/next 3 days, alerts if found |
| 25 | Weekly Brain Digest | weekly Sun 18:00 | Qdrant, Ollama, Discord | "What I learned about you this week" — new facts + conversation summary |
| 26 | Refresh Obsidian Knowledge | daily 06:15 | SSH, `scripts/seed_second_brain.py` | Re-seeds `~/Obsidian/KodyBrain` into Qdrant (delete-by-source then re-insert), read-only — nothing writes back to the vault |

## Workflows That Take Automated Write Actions

Worth knowing which workflows *do things* versus which only alert, since these deserve a closer look before activating:

- **09** restarts containers (Sonarr/Radarr/qBittorrent) automatically.
- **12** disables Prowlarr indexers automatically.
- **13** approves or declines Overseerr requests automatically.
- **16** approves an Overseerr request automatically (at most once/week).
- **10** commits to git automatically (but does not push — that step was deliberately left manual).
- **18** writes new facts into Qdrant whenever the classifier detects a "store" intent, logs every message it sees (conversation/photo entries), and **deletes** facts on a confidently-matched "forget" intent (score ≥ 0.75 as of 2026-08-25, only the single best match, only within `type: fact` points — never deletes conversation logs, photos, or journal entries). Before it deletes, it snapshots the fact into a `shadow_log` collection first, so the delete is recoverable. This is still the closest thing to a genuinely destructive automated action in this stack, but it's confidence-gated, single-target, shadow-logged, and always tells you exactly what it removed. The "correct" intent (added 2026-08-25) does the same delete+replace in one step for a confidently-matched old fact — same threshold, same shadow-logging.
- **20** writes a new Trilium note daily, if that credential is configured.
- **22** deletes-then-reinserts Qdrant points tagged with each refreshed doc's file path — scoped to `source` matching, never touches Discord-originated content (facts/conversations/photos/journal entries don't have file-path `source` values).
- **18** also creates real Vikunja tasks on a "task" intent, marks Vikunja tasks done on a confidently-matched "complete_task" intent (confidence ≥ 0.7, also shadow-logged before the write), and creates real Trilium notes on a "note" intent — all if the relevant credential is configured. It also writes/reads a `qa_cache` collection for repeated-question caching (self-managed, cleared automatically on any store/forget), and writes to `shadow_log` as noted above.
- **23** deletes conversation-log points older than 30 days — but only after successfully storing a summary of them first, so a failure mid-run can't lose data.
- **30** deletes `shadow_log` entries older than 90 days (retention, not correctness-critical — the digest already ran on that data first).

Everything else (01, 02, 03, 11, 14, 15, 27, 28, 29) only reads and alerts.

## Deliberate Design Choices Worth Remembering

- **SSH over docker.sock**: workflows that need host/container-level actions (09, 10, 11, 17) go through the `Mac Mini SSH` credential and run real shell scripts (`scripts/*.sh`) rather than mounting the Docker socket into n8n. Homepage's docker widget uses a different, narrower approach — a read-only `tecnativa/docker-socket-proxy` sidecar — because that's a continuously-running dashboard rather than a scheduled workflow.
- **Discord via webhook, not bot**, for alerting (01–12) — simplest setup, no bot/gateway needed. Workflow 17 is the one exception: it needs read access to channel messages, which webhooks can't do, so it uses a dedicated bot token polling the REST API every 30s instead of Discord's Gateway (websocket) or Interactions endpoint (requires cryptographic signature verification that couldn't be tested without a live Discord app during development).
- **No automated `git push`**: workflow 10's git snapshot commits locally only. An automated recurring push was flagged by a safety check as the kind of unattended action that should stay under explicit human control — add `&& git push origin main` to that workflow's SSH node yourself if you want it.
