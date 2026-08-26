# Immich

Self-hosted photo and video backup — the Google Photos replacement. Mobile auto-backup, albums, timeline, and (optionally) face grouping and smart search.

## Quick Facts

| | |
|---|---|
| **Image** | `ghcr.io/immich-app/immich-server:release` (v3.1.0 at deploy) + ML, Postgres, Redis |
| **Container name** | `immich-server`, `immich-machine-learning`, `immich-postgres`, `immich-redis` |
| **Compose file** | `immich/compose.yml` |
| **Port(s)** | `30042:2283` (server only; DB/Redis/ML are internal) |
| **Local URL** | `http://192.168.178.69:30042` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `/Volumes/media/immich` | `/data` | **the photo library** | On the NAS (23TB free), deliberately not the boot disk which only had 12GB free before this work |
| `immich/postgres` | `/var/lib/postgresql/data` | database | boot disk, gitignored |
| `immich/cache` | `/data`, `/cache` | Redis + ML model cache | gitignored |

## Dependencies

- **Depends on:** its own bundled Postgres (with vectorchord) and Redis. Optionally Authelia for SSO.
- **Depended on by:** nothing.

## Credentials & Secrets

`immich/.env` (gitignored) holds `DB_PASSWORD` and `OIDC_CLIENT_SECRET`; both also in Infisical (`IMMICH_DB_PASSWORD`, `OIDC_CLIENT_SECRET_IMMICH`). The first web user created becomes the admin.

## External Access

None currently. LAN only.

## Backups

**Not yet configured — worth doing before this holds real photos.** Two separate things need covering: the Postgres database (metadata, albums, faces) and `/Volumes/media/immich` (the actual files). The database is small and would fit the existing `pg_dump` pattern used for Infisical in workflow 03.

## Automation

None yet.

## Known Issues / Gotchas

- **Machine learning is deliberately throttled.** This box is CPU-only and shared with Ollama; a measured test earlier showed a third concurrent model dropped Ollama to 0.49 tokens/sec. The ML container is capped at 2 CPUs / 3GB and 1 worker. Face recognition and smart search will be *slow* on large imports — that's an accepted trade, not a bug.
- If ML ever becomes a problem, `docker stop immich-machine-learning` degrades gracefully: upload, browsing, and albums keep working; only smart search and face grouping stop.
- Immich's docs ask for 6GB RAM minimum; this deployment runs under that by throttling ML. Watch for OOM behaviour on very large imports.

## Change Log

- `2026-08-26` — Built. Library placed on the NAS, ML throttled for Ollama coexistence, OIDC pre-wired.
