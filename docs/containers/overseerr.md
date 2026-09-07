# Overseerr (now Seerr)

Request management front-end — lets household members request movies/TV without touching Sonarr/Radarr directly; requests get approved (manually or automatically) and forwarded to the right *arr instance.

**Migrated from Overseerr to Seerr on 2026-08-29** (Overseerr's community-run successor project, following https://docs.seerr.dev/migration-guide/). Container name, host path, port, and public URL were all kept identical on purpose — everything downstream (n8n workflows, Homepage, the API key) needed zero changes. This doc keeps the old filename so existing cross-references elsewhere in the repo don't break.

## Quick Facts

| | |
|---|---|
| **Image** | `ghcr.io/seerr-team/seerr:latest` (was `lscr.io/linuxserver/overseerr:latest`) |
| **Container name** | `overseerr` (unchanged, deliberately — see below) |
| **Compose file** | `overseerr/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30023:5055` |
| **Local URL** | `http://192.168.178.69:30023` |
| **Public URL** | `https://request.kodyparton.com` (via NPM) |
| **PUID/PGID** | n/a as of the migration — the Seerr image runs as a fixed non-root `node` user (uid 1000), not configurable via env vars the way the old linuxserver.io image was |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `overseerr/config` | `/app/config` (was `/config` under the old image) | app config, sqlite db, logs | gitignored |

## Dependencies

- **Depends on:** Sonarr, Sonarr 4K, Radarr, Radarr 4K (forwards approved requests to whichever is configured), TMDB (metadata, public API).
- **Depended on by:** n8n workflows 13 and 16, Homepage.

## Credentials & Secrets

API key stored in `overseerr/config/settings.json` (`main.apiKey`), gitignored — **survived the migration unchanged**, verified live (`GET /api/v1/request/count` with the existing key still works). Referenced by:
- n8n credential **"Overseerr API Key"**
- Homepage's `.env` as `HOMEPAGE_VAR_OVERSEERR_API_KEY`

## External Access

NPM proxy host `request.kodyparton.com` → `192.168.178.69:30023`, SSL forced, working correctly (unaffected by the migration — same container name, same host port).

## Backups

Not currently covered by workflow 03 (no scheduled-backup feature comparable to the *arr apps) — its sqlite db lives in `config/db/`, gitignored. A one-off pre-migration backup (`overseerr/config_backup_pre_seerr_migration_*.tar.gz`, gitignored via the repo's `*.tar.gz` rule) was taken 2026-08-29 and kept as a rollback point. If this needs proper ongoing backup coverage later, add it to `scripts/backup_check.sh`.

## Automation

- **13 - Smart Overseerr Triage** — on new request, checks TMDB watch/providers; auto-declines if already on a subscribed streaming service, auto-approves otherwise. Requires the app's own webhook (Settings → Notifications → Webhook) pointed at this workflow's URL. Unaffected by the migration — same API, same webhook config, survived in `settings.json`.
- **16 - Earned It (Strava-Gated Media Unlock)** — auto-approves the oldest pending request once a week, triggered by a new Strava activity.
- **02 - Docker Drift Detection** — will now compare against `ghcr.io/seerr-team/seerr:latest` instead of the old linuxserver.io image; nothing to change here, it just tracks whatever's declared in compose.yml.

## Known Issues / Gotchas

- Two separate n8n workflows (13 and 16) both call the approve/decline endpoints — if both are active, a request could in principle be approved by 16 before 13's triage logic ever sees it. Not a bug today (16 only fires weekly, at most once), but worth remembering if either workflow's timing changes.
- **Migration notes (2026-08-29):** the new image runs as a fixed non-root user baked in, not via `PUID`/`PGID` env vars like the old linuxserver.io image — those env vars were removed entirely from compose.yml since they'd be silently ignored. The guide calls for `chown -R 1000:1000` on the config volume; ran it, but macOS's bind-mount passthrough (via OrbStack) doesn't actually propagate uid/gid changes back to the host filesystem representation for local directories the way a real Linux host would (`ls -la` still shows the host user, not uid 1000) — this did **not** block the app from starting or writing, since macOS's bind-mount sharing is permissive for the mounting user's own files regardless of the nominal uid shown. The app's own log line confirms success either way: `[Seerr Migration]: Yeah! Overseerr to Seerr migration completed successfully!`. Verified post-migration: settings intact (`streamingRegion: US`, 4K enabled, etc. — not defaults), 224 requests preserved, existing API key still authenticates.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-29` — Migrated from Overseerr to Seerr (`ghcr.io/seerr-team/seerr:latest`). Config, requests, settings, and API key all confirmed intact post-migration.
