# Radarr

Movie library manager — the Sonarr equivalent for movies. Searches indexers via Prowlarr, sends grabs to qBittorrent, imports into the movie library.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/radarr:latest` |
| **Container name** | `radarr` |
| **Compose file** | `radarr/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30025:7878` |
| **Local URL** | `http://192.168.178.69:30025` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `radarr/config` | `/config` | app config, database, logs, scheduled backups | gitignored |
| `/Volumes/media/movies` | `/mnt/movies` | movie library root | SMB share — see known issue |
| `/Volumes/downloads` | `/mnt/downloads` | shared download staging dir | SMB share |

## Dependencies

- **Depends on:** Prowlarr, qBittorrent.
- **Depended on by:** Overseerr, Unpackerr, Homepage, several n8n workflows.

## Credentials & Secrets

API key in `radarr/config/config.xml`, gitignored. Referenced by:
- `unpackerr/.env` as `UN_RADARR_0_API_KEY`
- n8n credential **"Radarr API Key"**
- Homepage's `.env` as `HOMEPAGE_VAR_RADARR_API_KEY`

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backups in `radarr/config/Backups/scheduled/`, verified by workflow **03 - Backup Verification** (9-day stale threshold).

## Automation

**02, 03, 09** (`/mnt/movies`), **12, 13, 14, 15**, plus Unpackerr.

## Known Issues / Gotchas

- Same SMB-passthrough mount fragility as Sonarr — root cause documented on that page. Self-healed by workflow 09.

## Change Log

- `2026-08-24` — Doc created.
