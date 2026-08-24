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
| `/Users/kp-srv-01/mnt/downloads` | `/mnt/downloads` | downloads folder to watch/extract in | **Note:** this path is `~/mnt/downloads`, not `/Volumes/downloads` like every other service — check this is actually the same underlying share if debugging extraction issues. |

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

- The mount path discrepancy noted above (`~/mnt/downloads` vs. `/Volumes/downloads`) hasn't caused an observed problem, but hasn't been explicitly verified to point at the identical share either — worth double-checking if unpackerr ever seems to miss an extraction.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-17` — Moved 4 hardcoded API keys out of `compose.yml` into a gitignored `.env`.
