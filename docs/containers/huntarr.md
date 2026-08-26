# Huntarr

Background "missing/upgrade" search automation for the *arr apps — periodically triggers searches for missing episodes/movies and quality upgrades that would otherwise only happen on RSS sync or manual search.

## Quick Facts

| | |
|---|---|
| **Image** | `huntarr/huntarr:latest` |
| **Container name** | `huntarr` |
| **Compose file** | `huntarr/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30036:9705` |
| **Local URL** | `http://192.168.178.69:30036` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | n/a (not a linuxserver image) |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `huntarr/config` | `/config` | app config, scheduled backups | gitignored |

## Dependencies

- **Depends on:** Sonarr, Sonarr 4K, Radarr, Radarr 4K (connects to their APIs, configured inside Huntarr's own UI, not via env vars).
- **Depended on by:** Homepage (status widget).

## Credentials & Secrets

Huntarr stores its own copies of the *arr apps' API keys internally, in its own SQLite DB (`huntarr/config/huntarr.db`) — separate from this repo's `.env`/credential conventions, not tracked here. Set via `POST /api/settings/<app>` (see change log) using the same key values now also stored in Infisical (`SONARR_API_KEY`, `SONARR_4K_API_KEY`, `RADARR_API_KEY`, `RADARR_4K_API_KEY`) — if these ever get rotated, Huntarr's copies need updating too, it won't pick up a change made anywhere else automatically.

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backups in `huntarr/config/backups/`, verified by workflow **03 - Backup Verification** — stale threshold 5 days (backs up roughly every 3 days).

## Automation

- **02 - Docker Drift Detection**
- **03 - Backup Verification**

## Known Issues / Gotchas

- ~~Stray duplicate `tautulli/huntarr/compose.yml`~~ — removed 2026-08-25.

## Change Log

- `2026-08-26` — **Found genuinely broken since deployment (Jan 2026)**: both the Sonarr and Radarr instance configs had empty `api_key`/`api_url` fields — Radarr's address was even set to `http://localhost:7878`, unreachable from inside the container. Its own `/api/stats` confirmed `hunted: 0, upgraded: 0` across every app, for its entire ~7-month runtime — it had never successfully searched for anything. Fixed via `POST /api/settings/<app>` (the actual save endpoint — `/api/settings` itself is read-only, returns 405 on write) with real API keys pulled from Infisical, and added second instances for Sonarr 4K and Radarr 4K (previously only the standard tier was even attempted). Verified immediately after: found 428 real missing episodes, triggered a real season search, `hunted` count moved from 0 to 3 within a minute of the fix. Also learned: the `Loaded schedules: {'global': 0, ...}` debug line seen in its logs is **not** a "hunting disabled" signal despite looking like one — hunting worked fine with that still at 0, it's an unrelated scheduling-window feature that just happens to log at 0 by default.
- `2026-08-24` — Doc created.
