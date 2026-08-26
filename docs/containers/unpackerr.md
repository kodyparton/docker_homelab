# Unpackerr

Watches the shared downloads folder and extracts archives (rar/zip/etc.) that Sonarr/Radarr can't handle natively, for all 4 *arr instances.

## Quick Facts

| | |
|---|---|
| **Image** | `golift/unpackerr` |
| **Container name** | `unpackerr` |
| **Compose file** | `unpackerr/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | none (no web UI) |
| **Local URL** | n/a |
| **Public URL** | n/a |
| **PUID/PGID** | runs as explicit `user: 1001:988` (not the usual 1000/1000) |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `/Volumes/downloads` | `/mnt/downloads` | downloads folder to watch/extract in | Fixed 2026-08-26 — was pointed at `~/mnt/downloads`, a completely different, empty local directory, not an alias for the real share. |

## Dependencies

- **Depends on:** Sonarr, Sonarr 4K, Radarr, Radarr 4K (polls each directly via API to know what's expected).
- **Depended on by:** nothing.

## Credentials & Secrets

Four API keys, one per *arr instance, live in `unpackerr/.env` (gitignored, real values) with `unpackerr/.env.example` (placeholders, committed) as the template. Compose references them via `${UN_SONARR_0_API_KEY}` etc. — this was the very first credential-hygiene fix made in this repo (2026-08-17), before the `.gitignore` even existed; previously these were hardcoded directly in `compose.yml`.

## External Access

n/a — no web UI, outbound-only.

## Backups

n/a — stateless, no config worth backing up beyond the `.env`.

## Automation

- **02 - Docker Drift Detection**

## Known Issues / Gotchas

None currently open — see change log for the mount fix.

## Change Log

- `2026-08-26` — **Found genuinely broken since setup**: the mount path (`~/mnt/downloads`) was not an alias for the real downloads share, it was an entirely separate, empty local directory — Sonarr/Radarr place completed downloads at `/Volumes/downloads`, and Unpackerr could never see them, permanently failing with "no such file or directory" for every completed item, retried forever. The wrong directory also held 55MB of Unpackerr's own rotated log files (`UN_LOG_FILE` was set to write inside the same broken path) — deleted, and `UN_LOG_FILE` removed entirely in favor of plain `docker logs` output. Fixed the volume mount to `/Volumes/downloads:/mnt/downloads`, matching every other service; verified live — the "no such file" errors stopped immediately and previously-stuck items were found correctly on restart.
- `2026-08-24` — Doc created.
- `2026-08-17` — Moved 4 hardcoded API keys out of `compose.yml` into a gitignored `.env`.
