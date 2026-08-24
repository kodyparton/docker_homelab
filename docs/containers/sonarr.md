# Sonarr

TV show library manager — monitors for new episodes, searches indexers (via Prowlarr), sends grabs to qBittorrent, imports finished downloads into the TV library.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/sonarr:latest` |
| **Container name** | `sonarr` |
| **Compose file** | `sonarr/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30027:8989` |
| **Local URL** | `http://192.168.178.69:30027` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `sonarr/config` | `/config` | app config, database, logs, scheduled backups | gitignored |
| `/Volumes/media/tv` | `/mnt/tv` | TV library root | SMB share from UniFi Drive NAS — see known issue below |
| `/Volumes/downloads` | `/mnt/downloads` | shared download staging dir with qBittorrent | SMB share, same known issue |

## Dependencies

- **Depends on:** Prowlarr (indexers, synced automatically), qBittorrent (download client).
- **Depended on by:** Overseerr (creates requests here), Unpackerr (extracts archives it can't handle natively), Homepage (status widget), several n8n workflows.

## Credentials & Secrets

API key lives in `sonarr/config/config.xml` (`<ApiKey>`), gitignored — never committed. Referenced by:
- `unpackerr/.env` as `UN_SONARR_0_API_KEY`
- n8n credential **"Sonarr API Key"** (`httpHeaderAuth`, header `X-Api-Key`)
- Homepage's `.env` as `HOMEPAGE_VAR_SONARR_API_KEY`

## External Access

Not exposed via Nginx Proxy Manager — LAN-only.

## Backups

Sonarr's built-in scheduled backup writes zips to `sonarr/config/Backups/scheduled/`. Verified daily by n8n workflow **03 - Backup Verification** (`scripts/backup_check.sh`) — stale threshold 9 days, matches its weekly backup schedule.

## Automation

- **01 - Certificate & Domain Expiry Monitor** — n/a (not a domain)
- **02 - Docker Drift Detection** — checks image matches compose.yml
- **03 - Backup Verification** — checks backup freshness/integrity
- **09 - Mount Health Self-Healer** — checks `/mnt/tv` is readable, auto-restarts if not
- **12 - Flaky Indexer Auto-Healer** — indirectly benefits (disables bad Prowlarr indexers that would otherwise cause failed grabs here)
- **13 - Smart Overseerr Triage** — Overseerr approvals land here as monitored series
- **14 - Weekly Media Server Digest** — library size (series count)
- **15 - Release Radar Digest** — upcoming episode calendar
- **unpackerr** — polls this instance directly to extract completed downloads

## Known Issues / Gotchas

- **SMB mount instability (root-caused 2026-08-24):** `/mnt/tv` and `/mnt/downloads` are SMB shares mounted on the macOS host and passed through OrbStack's VM into the container. That passthrough intermittently drops the mount, causing `Mono.Unix.UnixIOException: No such file or directory (ENOENT)` inside Sonarr's free-space check, which cascades into failed imports until the container is restarted. Workflow 09 self-heals this every 15 minutes. A deeper fix (native CIFS mount from inside the container, bypassing the host passthrough) was scoped but deferred — needs NAS SMB credentials to implement.

## Change Log

- `2026-08-24` — Doc created. Root-caused the SMB mount issue, built self-healer (workflow 09).
