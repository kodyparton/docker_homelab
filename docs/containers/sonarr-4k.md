# Sonarr 4K

Second Sonarr instance dedicated to 4K TV releases, kept separate from the standard-quality library so quality profiles and root folders don't collide.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/sonarr:latest` |
| **Container name** | `sonarr-4k` |
| **Compose file** | `sonarr-4k/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30030:8989` |
| **Local URL** | `http://192.168.178.69:30030` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `sonarr-4k/config` | `/config` | app config, database, logs, scheduled backups | gitignored |
| `/Volumes/media/tv-4k` | `/mnt/tv-4k` | 4K TV library root | SMB share, same passthrough issue as regular Sonarr |
| `/Volumes/downloads` | `/mnt/downloads` | shared download staging dir | SMB share |

## Dependencies

- **Depends on:** Prowlarr, qBittorrent.
- **Depended on by:** Overseerr (4K requests), Unpackerr, Homepage, several n8n workflows.

## Credentials & Secrets

API key in `sonarr-4k/config/config.xml`, gitignored. Referenced by:
- `unpackerr/.env` as `UN_SONARR_1_API_KEY`
- n8n credential **"Sonarr 4K API Key"**
- Homepage's `.env` as `HOMEPAGE_VAR_SONARR_4K_API_KEY`

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backups in `sonarr-4k/config/Backups/scheduled/`, verified by workflow **03 - Backup Verification** (9-day stale threshold).

## Automation

Same set as regular Sonarr: **02, 03, 09, 12, 13, 14, 15**, plus Unpackerr.

## Known Issues / Gotchas

- Same SMB-passthrough mount fragility as regular Sonarr — see that doc for the full root cause. Self-healed by workflow 09 (`/mnt/tv-4k`).

## Change Log

- `2026-08-24` — Doc created.
