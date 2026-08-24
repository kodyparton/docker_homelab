# Radarr 4K

Second Radarr instance dedicated to 4K movie releases, kept separate from the standard-quality library.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/radarr:latest` |
| **Container name** | `radarr-4k` |
| **Compose file** | `radarr-4k/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30031:7878` |
| **Local URL** | `http://192.168.178.69:30031` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `radarr-4k/config` | `/config` | app config, database, logs, scheduled backups | gitignored |
| `/Volumes/media/movies-4k` | `/mnt/movies-4k` | 4K movie library root | SMB share, same passthrough issue |
| `/Volumes/downloads` | `/mnt/downloads` | shared download staging dir | SMB share |

## Dependencies

- **Depends on:** Prowlarr, qBittorrent.
- **Depended on by:** Overseerr (4K requests), Unpackerr, Homepage, several n8n workflows.

## Credentials & Secrets

API key in `radarr-4k/config/config.xml`, gitignored. Referenced by:
- `unpackerr/.env` as `UN_RADARR_1_API_KEY`
- n8n credential **"Radarr 4K API Key"**
- Homepage's `.env` as `HOMEPAGE_VAR_RADARR_4K_API_KEY`

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backups in `radarr-4k/config/Backups/scheduled/`, verified by workflow **03 - Backup Verification**.

## Automation

**02, 03, 09** (`/mnt/movies-4k`), **12, 13, 14, 15**, plus Unpackerr.

## Known Issues / Gotchas

- Same SMB-passthrough mount fragility as the other *arr apps. Self-healed by workflow 09.

## Change Log

- `2026-08-24` — Doc created.
