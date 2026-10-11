# Prowlarr

Indexer manager — the single place indexers/trackers are configured, syncing them out to Sonarr/Radarr (all 4 instances) automatically so nothing needs configuring per-app.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/prowlarr:latest` |
| **Container name** | `prowlarr` |
| **Compose file** | `prowlarr/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `9696:9696` |
| **Local URL** | `http://192.168.178.69:9696` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `prowlarr/config` | `/config` | app config, database, indexer definitions, logs, scheduled backups | gitignored |

No media/download mounts — Prowlarr only talks to indexers and to the *arr apps' APIs, it never touches files directly.

## Dependencies

- **Depends on:** nothing internal (talks outward to indexer sites).
- **Depended on by:** Sonarr, Sonarr 4K, Radarr, Radarr 4K, **Mylar3** (all pull indexer config from here through Prowlarr's full sync), Homepage (status widget), n8n workflow 12.

## Credentials & Secrets

API key in `prowlarr/config/config.xml`, gitignored. Referenced by:
- n8n credential **"Prowlarr API Key"**
- Homepage's `.env` as `HOMEPAGE_VAR_PROWLARR_API_KEY`

## External Access

Not exposed via NPM — LAN-only.

## Backups

Scheduled backups in `prowlarr/config/Backups/scheduled/`, verified by workflow **03 - Backup Verification**.

## Automation

- **02 - Docker Drift Detection**
- **03 - Backup Verification**
- **12 - Flaky Indexer Auto-Healer** — polls `/api/v1/indexerstats` every 6h, computes per-indexer failure-rate deltas, auto-disables any indexer with >50% failures over a rolling interval (min 5 queries sampled), posts to Discord. Re-enabling a disabled indexer is manual (in Prowlarr's UI).

## Known Issues / Gotchas

- ~~**Every app entry pointed at an old address**~~ — **FIXED 2026-10-11.** Sonarr, Sonarr 4K, Radarr and Radarr 4K had `prowlarrUrl`/`baseUrl` `http://10.10.0.130:…` (the Mac Mini's address on a previous network), so health said "All applications are unavailable due to failures for more than 6 hours", and Prowlarr couldn't push indexer changes (searches still worked because the indexers inside the apps had been hand-pointed at `192.168.178.69:9696`). All four were repointed to `http://192.168.178.69:<port>` (`prowlarrUrl` `http://192.168.178.69:9696`), with API keys taken from Infisical. Prowlarr's on-save connection test passed for each. The dead `Readarr` entry (`10.10.1.5`, nothing there; Prowlarr's scheduled backups still hold it) was deleted. A full sync then completed, and the health error is gone.
- **Full sync only pushes an indexer to an app whose categories it shares.** After the fix, Sonarr and Radarr still hold exactly `IPTorrents (Prowlarr)`. ABtorrents and Ebooks-Shares are audiobook/ebook trackers (categories 3000/7000), so they never sync to the TV/movie apps; only comic-capable ones (`7030`) reach Mylar3.
- ~~**The qBittorrent download client pointed at `10.10.0.130`**~~ — **FIXED 2026-10-11** (host → `192.168.178.69`; the on-save test passed with the stored credentials). Grabbing by hand from Prowlarr's search page works again.
- **`Ebooks-Shares` has no definition** (the tracker's definition is gone from Prowlarr). **Disabled 2026-10-11** rather than deleted, which keeps the tracker login in case the definition returns. It now syncs to Mylar3 as disabled. The "no definition" health warning stays until it's deleted.
- **"Allowed Hosts is not configured"** (warning): Prowlarr answers for any hostname. It's worth setting to `prowlarr.kodyparton.com, 192.168.178.69` given the WAN port-forward exposure (`known-issues.md`).
- If workflow 12 disables an indexer, check Discord for why before re-enabling — it's evidence-based, not a guess.

## Change Log

- `2026-10-11` (later) — **Fixed the stale addresses** at Kody's request: 4 apps + the qBittorrent client → `192.168.178.69` (each passed the on-save connection test), dead `Readarr` app deleted, `Ebooks-Shares` disabled. Full sync completed; "All applications are unavailable" cleared. Verified IPTorrents returns comics (category 7030): 100 results each for "Batman" and "Spider-Man".
- `2026-10-11` — Added app **Mylar3** (id 6, full sync, category 7030 → `http://192.168.178.69:30046`; connection test passed, 2 providers synced). Documented the stale `10.10.x` app and download-client addresses and the broken Ebooks-Shares definition (not changed; Kody's call).
- `2026-08-24` — Doc created.
