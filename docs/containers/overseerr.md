# Overseerr

Request management front-end — lets household members request movies/TV without touching Sonarr/Radarr directly; requests get approved (manually or automatically) and forwarded to the right *arr instance.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/overseerr:latest` |
| **Container name** | `overseerr` |
| **Compose file** | `overseerr/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30023:5055` |
| **Local URL** | `http://192.168.178.69:30023` |
| **Public URL** | `https://request.kodyparton.com` (via NPM) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `overseerr/config` | `/config` | app config, sqlite db, logs | gitignored |

## Dependencies

- **Depends on:** Sonarr, Sonarr 4K, Radarr, Radarr 4K (forwards approved requests to whichever is configured), TMDB (metadata, public API).
- **Depended on by:** n8n workflows 13 and 16, Homepage.

## Credentials & Secrets

API key stored in `overseerr/config/settings.json` (`main.apiKey`), gitignored. Referenced by:
- n8n credential **"Overseerr API Key"**
- Homepage's `.env` as `HOMEPAGE_VAR_OVERSEERR_API_KEY`

## External Access

NPM proxy host `request.kodyparton.com` → `192.168.178.69:30023`, SSL forced, working correctly.

## Backups

Not currently covered by workflow 03 (no scheduled-backup feature comparable to the *arr apps) — its sqlite db lives in `config/db/`, gitignored. If this needs proper backup coverage later, add it to `scripts/backup_check.sh`.

## Automation

- **13 - Smart Overseerr Triage** — on new request, checks TMDB watch/providers; auto-declines if already on a subscribed streaming service, auto-approves otherwise. Requires Overseerr's own webhook (Settings → Notifications → Webhook) pointed at this workflow's URL.
- **16 - Earned It (Strava-Gated Media Unlock)** — auto-approves the oldest pending request once a week, triggered by a new Strava activity.
- **02 - Docker Drift Detection**

## Known Issues / Gotchas

- Two separate n8n workflows (13 and 16) both call Overseerr's approve/decline endpoints — if both are active, a request could in principle be approved by 16 before 13's triage logic ever sees it. Not a bug today (16 only fires weekly, at most once), but worth remembering if either workflow's timing changes.

## Change Log

- `2026-08-24` — Doc created.
