# n8n Automation Map

All workflows live in the `n8n` container (`https://n8n.kodyparton.com`). Every workflow is created **inactive** by default — n8n's public API cannot activate workflows, so each one is a deliberate manual toggle after its credentials are confirmed real. See each workflow's manual-setup steps (given when it was built) for exact credential requirements.

## Shared Credentials

| Credential name | Type | Used by |
|---|---|---|
| `Mac Mini SSH` | `sshPassword` | 01, 02, 03, 09, 10, 11, 17 |
| `Homelab Discord Webhook` | `discordWebhookApi` | 01, 02, 03, 09, 10, 11, 12 |
| `Sonarr API Key` / `Sonarr 4K API Key` | `httpHeaderAuth` | 14, 15 |
| `Radarr API Key` / `Radarr 4K API Key` | `httpHeaderAuth` | 14, 15 |
| `Prowlarr API Key` | `httpHeaderAuth` | 12 |
| `Overseerr API Key` | `httpHeaderAuth` | 13 |
| `Tautulli API Key` | `httpQueryAuth` | 14 |
| `Entra Graph (App-Only)` | `oAuth2Api` | 04a, 04b |
| `Job Pipeline Notion` | `notionApi` | 05 |
| `Earned It Discord Webhook` | `discordWebhookApi` | 16 (placeholder, not yet real) |

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

## Workflows That Take Automated Write Actions

Worth knowing which workflows *do things* versus which only alert, since these deserve a closer look before activating:

- **09** restarts containers (Sonarr/Radarr/qBittorrent) automatically.
- **12** disables Prowlarr indexers automatically.
- **13** approves or declines Overseerr requests automatically.
- **16** approves an Overseerr request automatically (at most once/week).
- **10** commits to git automatically (but does not push — that step was deliberately left manual).

Everything else (01, 02, 03, 11, 14, 15) only reads and alerts.

## Deliberate Design Choices Worth Remembering

- **SSH over docker.sock**: workflows that need host/container-level actions (09, 10, 11, 17) go through the `Mac Mini SSH` credential and run real shell scripts (`scripts/*.sh`) rather than mounting the Docker socket into n8n. Homepage's docker widget uses a different, narrower approach — a read-only `tecnativa/docker-socket-proxy` sidecar — because that's a continuously-running dashboard rather than a scheduled workflow.
- **Discord via webhook, not bot**, for alerting (01–12) — simplest setup, no bot/gateway needed. Workflow 17 is the one exception: it needs read access to channel messages, which webhooks can't do, so it uses a dedicated bot token polling the REST API every 30s instead of Discord's Gateway (websocket) or Interactions endpoint (requires cryptographic signature verification that couldn't be tested without a live Discord app during development).
- **No automated `git push`**: workflow 10's git snapshot commits locally only. An automated recurring push was flagged by a safety check as the kind of unattended action that should stay under explicit human control — add `&& git push origin main` to that workflow's SSH node yourself if you want it.
