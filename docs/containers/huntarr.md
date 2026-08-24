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

Huntarr stores its own copies of the *arr apps' API keys internally (entered via its UI), separate from this repo's `.env`/credential conventions — not tracked here.

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backups in `huntarr/config/backups/`, verified by workflow **03 - Backup Verification** — stale threshold 5 days (backs up roughly every 3 days).

## Automation

- **02 - Docker Drift Detection**
- **03 - Backup Verification**

## Known Issues / Gotchas

- There's a stray duplicate `tautulli/huntarr/compose.yml` file in the repo (identical content to the real `huntarr/compose.yml`) that isn't actually deployed as a separate service — only one `huntarr` container runs. Leftover from an earlier reorganization; harmless but confusing, worth deleting eventually.

## Change Log

- `2026-08-24` — Doc created.
