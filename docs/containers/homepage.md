# Homepage

Dashboard aggregating every self-hosted service in this stack into one page, with live status widgets pulled from each service's own API and per-container CPU/memory via a locked-down Docker socket proxy.

## Quick Facts

| | |
|---|---|
| **Image** | `ghcr.io/gethomepage/homepage:latest` (+ sidecar `tecnativa/docker-socket-proxy:latest`) |
| **Container name** | `homepage` (+ `homepage-socket-proxy`) |
| **Compose file** | `homepage/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `3000:3000` |
| **Local URL** | `http://192.168.178.69:3000` |
| **Public URL** | `https://home.kodyparton.com` (internal-only, see External Access) |
| **PUID/PGID** | n/a |
| **Timezone** | container default |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `homepage/config` | `/app/config` | dashboard YAML config (desired-state, tracked in git — see below) | `.gitignore` carves out an exception here since this is config-as-code, not runtime state |
| `/var/run/docker.sock` | (socket-proxy only) `/var/run/docker.sock:ro` | read-only container status | never mounted into the `homepage` container itself — only into the hardened proxy sidecar |

## Dependencies

- **Depends on:** `homepage-socket-proxy` (for container CPU/mem/status), and the live API of every service it shows a widget for (Sonarr×2, Radarr×2, Prowlarr, Overseerr, Tautulli, qBittorrent).
- **Depended on by:** nothing — it's a read-only view layer.

## Credentials & Secrets

`homepage/.env` (gitignored) holds real API keys for every widget as `HOMEPAGE_VAR_*` variables, referenced in `config/services.yaml` via `{{HOMEPAGE_VAR_...}}` templating — never hardcoded directly. `.env.example` is the committed placeholder template. qBittorrent's password entry is still a weak default value, not the real WebUI password — see `docs/architecture/secrets-and-rotation.md`, flagged there as an active exposure worth fixing directly, independent of the Infisical migration.

## External Access

**In progress as of 2026-08-24**: `home.kodyparton.com` is intended to resolve only on the home network — a Cloudflare DNS A record (`home.kodyparton.com` → `192.168.178.69`, **DNS only**, not proxied) plus an NPM proxy host (→ `192.168.178.69:3000`, reusing the existing `*.kodyparton.com` wildcard cert rather than requesting a new one, since Let's Encrypt's HTTP-01 challenge can't reach a private IP). `HOMEPAGE_ALLOWED_HOSTS` in compose already allow-lists this hostname. **Both the DNS record and the NPM proxy host still need to be created manually** — see `docs/architecture/known-issues.md`.

## Backups

Not covered by `scripts/backup_check.sh` — its config is git-tracked YAML (see below), so "backup" mostly just means "don't lose git history."

## Automation

None — Homepage itself isn't touched by any n8n workflow (it's the dashboard, not an automation target).

## Known Issues / Gotchas

- `config/*.yaml` is deliberately tracked in git (an exception carved out of the repo-wide `*/config/` gitignore rule) — this is desired-state configuration, not runtime data, matching how `compose.yml` files are treated everywhere else in this repo. If you add new YAML config files here, confirm they're not accidentally excluded.
- Heimdall (an older dashboard app) was removed 2026-08-17 in favor of this — it was running but completely unconfigured, so nothing was lost.

## Change Log

- `2026-08-24` — Doc created. Added Vikunja to the dashboard. Began internal-URL setup (DNS + NPM steps still pending).
- `2026-08-17` — Built as Heimdall's replacement.
