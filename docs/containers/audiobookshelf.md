# Audiobookshelf

Audiobook and podcast server with its own web player and mobile app support.

## Quick Facts

| | |
|---|---|
| **Image** | `ghcr.io/advplyr/audiobookshelf:latest` |
| **Container name** | `audiobookshelf` |
| **Compose file** | `audiobookshelf/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30033:30033` |
| **Local URL** | `http://192.168.178.69:30033` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `/Volumes/media/audiobooks` | `/audiobooks` | audiobook library | SMB share |
| `audiobookshelf/podcasts` | `/podcasts` | podcast downloads | local disk, not SMB |
| `audiobookshelf/config` | `/config` | app config, sqlite db | gitignored |
| `audiobookshelf/metadata` | `/metadata` | covers, cache, scheduled backups | gitignored |

## Dependencies

- **Depends on:** nothing internal.
- **Depended on by:** Homepage (status widget).

## Credentials & Secrets

None referenced elsewhere in this repo currently — no API key wired into any n8n workflow or Homepage widget yet.

## External Access

Not exposed via NPM — LAN-only.

## Backups

Automatic backups were **disabled by default** (`backupSchedule: false` in its settings DB) and had never run. Fixed 2026-08-17 — enabled a daily 3am schedule (`backupSchedule: "0 3 * * *"`, `backupsToKeep: 2`), edited directly in `config/absdatabase.sqlite` while the container was stopped. Verified by workflow **03 - Backup Verification** — stale threshold 14 days, checked in `metadata/backups/`.

## Automation

- **02 - Docker Drift Detection**
- **03 - Backup Verification**

## Known Issues / Gotchas

- Its audiobook library mount (`/Volumes/media/audiobooks`) is the same class of SMB share as the *arr apps' mounts, but audiobookshelf is **not** currently covered by the mount health self-healer (workflow 09) — that workflow only watches the 5 mounts directly implicated in the original bug report (Sonarr/Radarr/qBittorrent). Worth adding if this mount ever shows the same ENOENT symptom.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-17` — Backups were silently disabled since setup; enabled a daily schedule.
