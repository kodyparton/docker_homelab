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
- **Depended on by:** Sonarr, Sonarr 4K, Radarr, Radarr 4K (all pull indexer config from here), Homepage (status widget), n8n workflow 12.

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

- None currently known specific to Prowlarr itself. If workflow 12 disables an indexer, check Discord for why before re-enabling — it's evidence-based, not a guess.

## Change Log

- `2026-08-24` — Doc created.
