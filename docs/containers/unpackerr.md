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

- **`paths` must be set explicitly and must match the volume target.** Unpackerr defaults to `/downloads` when no `UN_<APP>_<N>_PATHS_0` is given. This container mounts at `/mnt/downloads`, so the default points at a path that does not exist — and unpackerr does **not** treat that as an error. It starts cleanly, connects to all four *arr instances, retrieves their queues, logs nothing alarming, and extracts nothing, indefinitely. Any future change to the volume target must change these env vars in the same edit.
- **`latest` is load-bearing and has bitten this service.** Watchtower pulled a broken upstream build on 2026-08-30 (see change log). Consider pinning a version tag if it recurs.

## Change Log

- `2026-08-31` — **Found dead, then found a second bug behind it.** Container was sitting in `created` state with `exec: "/unpackerr": permission denied` (exit 126), so nothing had been extracted since 2026-08-30. Root cause was upstream, not local: `/unpackerr` in the `golift/unpackerr` arm64 image built 2026-08-30 22:34 shipped as `-rw-r--r--` — not executable by anyone, root included, so the `user: 1000:1000` setting was a red herring. Watchtower had pulled it. Upstream fixed it the same day in `v0.16.1` (`-rwxr-xr-x`, byte-identical size, confirming a pure permission-bit packaging fault); verified the new image's mode in a throwaway container *before* recreating anything. Note `scripts/cifs_volume_health_check.sh` correctly does **not** cover this — it matches volume-mount errors in `.State.Error`, and this was an exec fault, so nothing was healing it. **Second bug, found only because the first was fixed:** with the container finally running, its startup log showed `paths:["/downloads"]` while the volume mounts at `/mnt/downloads` — `/downloads` does not exist in the container. No `UN_*_PATHS_0` vars had ever been set, so it fell back to the built-in default. Same class as the 2026-08-26 finding: the *mount* was corrected then, the app's own path config never was. Added `UN_SONARR_0/1_PATHS_0` and `UN_RADARR_0/1_PATHS_0=/mnt/downloads`; verified all four instances now log `paths:["/mnt/downloads"]` and retrieve real queues (21 Sonarr, 9 Sonarr-4K, 1 Radarr items).
- `2026-08-26` — **Found genuinely broken since setup**: the mount path (`~/mnt/downloads`) was not an alias for the real downloads share, it was an entirely separate, empty local directory — Sonarr/Radarr place completed downloads at `/Volumes/downloads`, and Unpackerr could never see them, permanently failing with "no such file or directory" for every completed item, retried forever. The wrong directory also held 55MB of Unpackerr's own rotated log files (`UN_LOG_FILE` was set to write inside the same broken path) — deleted, and `UN_LOG_FILE` removed entirely in favor of plain `docker logs` output. Fixed the volume mount to `/Volumes/downloads:/mnt/downloads`, matching every other service; verified live — the "no such file" errors stopped immediately and previously-stuck items were found correctly on restart.
- `2026-08-24` — Doc created.
- `2026-08-17` — Moved 4 hardcoded API keys out of `compose.yml` into a gitignored `.env`.
