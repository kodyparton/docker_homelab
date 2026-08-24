# Tautulli

Plex watch-statistics tracker — monitors a Plex Media Server (not itself part of this compose repo) and records what's watched, by whom, and when.

## Quick Facts

| | |
|---|---|
| **Image** | `ghcr.io/tautulli/tautulli` |
| **Container name** | `tautulli` |
| **Compose file** | `tautulli/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30035:8181` |
| **Local URL** | `http://192.168.178.69:30035` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `tautulli/config` | `/config` | app config, database, logs, scheduled backups | gitignored |

## Dependencies

- **Depends on:** a Plex Media Server (external to this repo, not documented here).
- **Depended on by:** Homepage (status widget), n8n workflow 14.

## Credentials & Secrets

API key in `tautulli/config/config.ini` (`api_key`), gitignored. Referenced by:
- n8n credential **"Tautulli API Key"**
- Homepage's `.env` as `HOMEPAGE_VAR_TAUTULLI_API_KEY`

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backups land in `tautulli/config/backups/`, verified by workflow **03 - Backup Verification** — stale threshold 2 days (Tautulli backs up roughly every 6h, much more frequently than the *arr apps).

## Automation

- **02 - Docker Drift Detection**
- **03 - Backup Verification**
- **14 - Weekly Media Server Digest** — pulls `get_home_stats` (top watched titles/users for the week).

## Known Issues / Gotchas

None currently known.

## Change Log

- `2026-08-24` — Doc created.
