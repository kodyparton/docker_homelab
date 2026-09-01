# Plex Media Server

The media server the whole *arr chain ultimately feeds. **Not a container** — it runs as the native macOS app on the Mac Mini, which is deliberate and load-bearing (see "Why not containerized" below). Documented here anyway because it is now actively configured by this repo, and because it is the last remaining consumer of the macOS-host SMB passthrough that everything else migrated off on 2026-08-29.

## Quick Facts

| | |
|---|---|
| **Image** | _n/a — native macOS app_, `/Applications/Plex Media Server.app` |
| **Container name** | _n/a_ |
| **Compose file** | _none_ |
| **Host** | Mac Mini (`192.168.178.69`), Apple M1, 16GB, 8 cores (4P/4E) |
| **Port(s)** | `32400` |
| **Local URL** | `http://192.168.178.69:32400/web` |
| **Public URL** | _none via NPM_ — reached over Plex's own `plex.direct` relay/remote access |
| **PUID/PGID** | _n/a_ — runs as the `kp-srv-01` login user |
| **Timezone** | macOS system timezone (not the stack's `TZ` env convention) |
| **Restart policy** | _n/a_ — launched as a login item |

## Volumes / Mounts

| Host path | Purpose | Notes |
|---|---|---|
| `~/Library/Application Support/Plex Media Server` → **symlink** → `/Volumes/FastSSD/PlexData` | Metadata, bundles, and the live SQLite library DB | Moved to the external USB SSD 2026-08-27 (storage plan Phase 2) to reclaim 12GB of boot disk. **This is a live database on a detachable drive**, which `storage-plan.md` itself argues against — see Known Issues. |
| `/Volumes/FastSSD/PlexTranscode` | Transcoder temp/scratch | Added 2026-08-31. Previously unset, which meant scratch defaulted *inside* `PlexData`. |
| `/Volumes/media` (smbfs → `//…@192.168.178.38/media`) | The actual media libraries | macOS-host SMB mount. Library section paths are stored as `/Volumes/media/...` inside Plex's own DB, so this path cannot change without re-pointing every section. |

## Why not containerized

Assessed 2026-08-31 and **deliberately rejected** for this hardware. Moving Plex into the stack would be attractive — it would get the proven `nas_*` native CIFS volumes instead of the flaky macOS passthrough, and come under the same compose/Watchtower/Uptime Kuma management as everything else. But OrbStack runs a Linux VM on Apple Silicon with **no GPU or VideoToolbox passthrough**, so a containerized Plex here is software-transcode-only. Kody's actual load is 4K and multiple concurrent transcodes, which software transcoding on an M1 cannot serve. Native macOS Plex can use VideoToolbox hardware acceleration; that capability is the reason this service stays outside the stack.

The corollary: the containerization option only reopens if Plex moves to hardware with a usable encoder (an Intel QuickSync box, or a newer Mac kept native).

## Dependencies

- **Depends on:** the `/Volumes/media` SMB mount from the UNAS Pro (`192.168.178.38`). Everything else in the stack now reaches that NAS via native CIFS instead; Plex is the sole remaining passthrough consumer.
- **Depended on by:** **Tautulli** (play-history stats), **Overseerr/Seerr** (availability checks), and the *arr chain indirectly — Sonarr/Radarr import files that Plex then picks up.

## Credentials & Secrets

- `PlexOnlineToken` and `.LocalAdminToken` both live inside `/Volumes/FastSSD/PlexData` (`Preferences.xml` and `.LocalAdminToken` respectively). Neither is in git — that whole directory is outside the repo.
- The local admin token is what `curl`-based pref changes against `http://127.0.0.1:32400/:/prefs` authenticate with.
- **Never print `Preferences.xml` with surrounding context** — `PlexOnlineToken` sits immediately adjacent to other keys and is trivially leaked by a wide `grep -o`. Match on specific attribute names only. (This happened 2026-08-31; that token was rotated.)

## External Access

No NPM proxy host. Unlike every other service, Plex is reached via its own remote-access mechanism and `plex.direct` URLs, not `*.kodyparton.com`. Tautulli's stored `pms_ip` is the stale `10.10.0.130` and still works only because it connects through a `plex.direct` URL — noted in `plex-cleanup-design.md`, still uncorrected.

## Backups

**None.** Plex's data directory is not in any backup rotation, and it now lives on a detachable drive. The library DB is regenerable in principle (rescan the NAS) but watch history, collections, and play state are not. This is a real gap — worth folding into workflow 03 alongside the Infisical/Qdrant backups that already write to the NAS.

## Automation

- `scripts/mount_health_check.sh` — detects the three ways `/Volumes/media` fails Plex (`host_mount_shadowed`, `host_mount_missing`, `host_mount_unresponsive`). Detect-only; not yet scheduled.
- `scripts/disk_maintenance.sh` — trims Plex's `PhotoTranscoder` cache once it exceeds 10GB.
- `scripts/plex_cleanup_candidates.py` — read-only "Leaving Soon" candidate report, see `docs/architecture/plex-cleanup-design.md` (design only, not built).
- No n8n workflow monitors Plex directly.

## Known Issues / Gotchas

- **Library DB is on a detachable USB SSD.** `storage-plan.md` tiers live databases onto the internal SSD explicitly, and Plex's is the one that ended up on USB anyway. Moving it back costs 12GB of a boot disk that currently has ~21GB free, which is why it hasn't moved. Unresolved tension, not an oversight.
- **`FastSSD` is mounted `noowners`** (`Owners: Disabled`). Harmless for Plex specifically, since it runs as the login user rather than a PUID-mapped container, but it is why nothing uid-sensitive can join it there.
- **`/Volumes/media` can be silently shadowed** after an unclean unmount, leaving Plex reading an empty stub while `mount` still looks healthy. Caused a 2+ hour outage on 2026-08-27.
- **A stale Docker-shaped value was found in `Preferences.xml`**: `TranscoderTempDirectory="/transcode"` — the `linuxserver/plex` convention, and a path that cannot exist on macOS's read-only root. The *running* server had rejected it and fallen back to empty, so it was never actively breaking transcodes, but on-disk prefs and running prefs disagreed on this and on the scan interval. Worth knowing that `Preferences.xml` is not a reliable read of live state — query `/:/prefs` instead.

## Change Log

- `2026-08-31` (later) — **Streaming still failing; root cause found to be the NAS, not Plex.** Sustained NAS reads measured at 245 kB/s–3.1 MB/s against a ~1.32 MB/s requirement for a single 1080p stream; full evidence and the list of ruled-out causes in `known-issues.md`. **Hardware transcoding was verified working** (10× realtime for 1080p from local disk) — retracting the earlier claim that it never engages, which misread normal audio-only-job log lines as a fault. Disabled six analysis behaviors that were set to `asap` and therefore bypassing the Butler window: `GenerateIntroMarkerBehavior`, `GenerateCreditsMarkerBehavior`, `GenerateAdMarkerBehavior`, `GenerateChapterThumbBehavior`, `LoudnessAnalysisBehavior`, `MusicAnalysisBehavior` → `never`; plus `ButlerTaskUpgradeMediaAnalysis=0`. Note the `/butler` endpoint's task names are **not** valid `/:/prefs` keys (HTTP 400) — use the `*Behavior` prefs. Confirmed `disksleep 0` had been applied and did not resolve the symptom, which is what redirected the investigation off the storage-tier theory.

- `2026-08-31` — Investigated "load times vary and sometimes hang entirely". Applied four pref changes via the local API (all verified against `/:/prefs` afterward, not just accepted on HTTP 200): `TranscoderTempDirectory` → `/Volumes/FastSSD/PlexTranscode` (was unset, so scratch defaulted into the data dir); `ScannerLowPriority` → `1`; `ButlerTaskDeepMediaAnalysis` → `0` (extensive nightly analysis across the SMB mount); `ScheduledLibraryUpdateInterval` pinned to `3600` to reconcile a disk/running mismatch. Confirmed already-correct: `GenerateBIFBehavior=never`, Butler window 02:00–05:00. **Still outstanding: `sudo pmset -a disksleep 0`** — disks sleep after 10 minutes and Plex's DB and transcode scratch both live on the drive that sleeps; this is the single most likely cause of the reported hangs and needs an interactive sudo. Assessed and rejected containerizing (see above).
- `2026-08-27` — Data directory (12GB) moved to `/Volumes/FastSSD/PlexData` via symlink as storage-plan Phase 2. DB verified byte-identical and all 4 libraries confirmed intact post-move.
- `2026-08-27` — "Media unavailable" outage: `/Volumes/media` shadowed by a stale stub after an SMB reconnect. Fixed with `sudo rmdir` + remount.
