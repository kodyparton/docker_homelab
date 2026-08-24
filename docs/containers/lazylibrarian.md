# LazyLibrarian

Ebook (and audiobook metadata) library manager — the *arr-style app for books, using Calibre for conversion via a Docker mod.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/lazylibrarian:latest` |
| **Container name** | `lazylibrarian` |
| **Compose file** | `lazylibrarian/config/compose.yml` (unusually nested one level under `config/`, not at the service root like every other service — a quirk from an earlier reorganization) |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30032:5299` |
| **Local URL** | `http://192.168.178.69:30032` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `lazylibrarian/config` | `/config` | app config, sqlite db, logs | gitignored |
| `/Volumes/downloads` | `/downloads` | download staging | SMB share |
| `/Volumes/media/books` | `/books` | book library root | SMB share |

Uses `DOCKER_MODS` (`universal-calibre` + `lazylibrarian-ffmpeg`) — these install extra packages into the container at every startup, which is why first-boot (or first-boot-after-recreate) takes noticeably longer than other services.

## Dependencies

- **Depends on:** nothing internal (talks to book-indexer sites directly, not via Prowlarr).
- **Depended on by:** Homepage (status widget).

## Credentials & Secrets

Not currently referenced by any n8n workflow or Homepage widget.

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backup as a single `.tgz` in `lazylibrarian/config/`, verified by workflow **03 - Backup Verification** — stale threshold 14 days.

## Automation

- **02 - Docker Drift Detection**
- **03 - Backup Verification**

## Known Issues / Gotchas

- **Port mismatch (fixed 2026-08-17):** compose used to map host `30032` to container port `30032`, but the app actually listens on `5299` internally — meaning it was completely unreachable via its published port even while "running." Fixed to `30032:5299`.
- **Container was found stopped (fixed 2026-08-17)**, with no crash in its logs — it had just never been restarted after being stopped at some point. Restarted; now running normally.
- Same SMB-share mount pattern as the *arr apps (`/downloads`, `/books`), but **not** covered by the mount health self-healer (workflow 09) — only the 5 mounts from the original bug report are watched.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-17` — Fixed port mapping (30032→5299) and restarted a stopped container.
