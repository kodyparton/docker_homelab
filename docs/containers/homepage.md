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

- **Depends on:** `homepage-socket-proxy` (for container CPU/mem/status), and the live API of every service it shows a widget for (Sonarr×2, Radarr×2, Prowlarr, Seerr, Tautulli, qBittorrent, Uptime Kuma). Also reaches the UNAS Pro (`192.168.178.38`) by ICMP for the reachability card, and `api.open-meteo.com` for weather — the only outbound WAN call the dashboard makes.
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

- **`disk: /app/config` in `widgets.yaml` is intentional, not a typo.** The `./config` bind mount is the only path in the container that crosses back to the real macOS filesystem, so it is the sole place the resources widget can measure the actual Mac Mini boot disk. The previous `disk: /` measured OrbStack's 58 GB VM overlay instead — a number that meant nothing. (As of 2026-08-30 the real figure is **89% full**, 245 GB total with ~26 GB free.)
- **The appliance cards (UNAS Pro, Ziggo Modem) `href` to their NPM names but health-check the raw IP.** That split is deliberate: browsing goes through `nas.`/`ziggo.kodyparton.com` so the browser gets the real wildcard cert with no warning, while `ping:` targets the device itself. Pointing the check at the NPM name instead would silently be testing the proxy rather than the hardware — and "is the NAS reachable?" is the question that actually matters, since a NAS blip kills every CIFS-mounted container.
- **Those cards use `ping:`, not `siteMonitor:`.** Both HTTP options fail against it: `https://` presents a self-signed cert that Homepage's fetch rejects, and `http://` 301-redirects to https, which Homepage's redirect follower refuses with `ERR_INVALID_PROTOCOL` (observed in the container logs, not theorised). ICMP needs neither and reports real round-trip latency.
- **The Uptime Kuma widget reads the public `default` status page**, so it needs no credential. Populate it with `scripts/kuma_seed_monitors.sh`. Beware a real trap here: Kuma returns HTTP 200 with empty lists for a status-page slug that **does not exist**, so an empty widget cannot be distinguished from a missing status page by hitting the endpoint — verify with `SELECT slug FROM status_page` against `uptime-kuma/data/kuma.db` instead.
- **Widgets requiring a credential are staged commented-out**, not shipped live, because Homepage renders a red error card for a widget whose key is empty. Each commented block names exactly where to generate its token, and the matching `HOMEPAGE_VAR_*` entry is in `.env.example`. Staged: Immich, Paperless, Audiobookshelf, Komga, AdGuard Home, Nginx Proxy Manager, and the UniFi console info widget.
- **The Ziggo Modem card is the WAN edge.** If it is down, an internet outage is explained by hardware no container-level check would account for. It is the only card on the dashboard representing something upstream of the whole homelab.
- **`custom.css` is now git-tracked** via an explicit `!homepage/config/custom.css` exception. It is the visual theme layer (gradient background, glass cards, status-dot glow) and is source, not runtime state — without the exception the repo-wide `homepage/config/*` rule would have dropped it on a re-clone. `custom.js` remains ignored (it is empty). The theme is deliberately CSS-only with no remote font or CDN image, so the dashboard looks right when WAN is down — which is exactly when it gets opened.
- Every group in `services.yaml` must also appear under `layout:` in `settings.yaml`, or it renders unstyled at the bottom of the page. `Personal` was missing this before 2026-08-30.
- `config/*.yaml` is deliberately tracked in git (an exception carved out of the repo-wide `*/config/` gitignore rule) — this is desired-state configuration, not runtime data, matching how `compose.yml` files are treated everywhere else in this repo. If you add new YAML config files here, confirm they're not accidentally excluded.
- Heimdall (an older dashboard app) was removed 2026-08-17 in favor of this — it was running but completely unconfigured, so nothing was lost.

## Change Log

- `2026-10-11` (night) — **Mylar3** card added under Media Management with a **live** widget (`HOMEPAGE_VAR_MYLAR_API_KEY` from Infisical through `scripts/env_from_infisical.py`). The `href` is the IP until Mylar has a login and a hostname. The **qBittorrent widget's password was stale**, which the auth bypass had hidden; it was refreshed from the corrected Infisical value, and the widget was verified to see all 300 torrents after the bypass was turned off.
- `2026-10-11` — Comics card added in the Personal group: first **YACReader**, then the same evening swapped to **Komga**, which replaced it. Container status `komga`, and the `komga` widget staged with `HOMEPAGE_VAR_KOMGA_USERNAME`/`_PASSWORD` (in `.env.example`). Komga's widget authenticates with a normal login; a non-admin user is enough.
- `2026-08-30` (later) — Repointed the UNAS Pro card's `href` from the raw IP to `https://nas.kodyparton.com` and added a **Ziggo Modem** card (`https://ziggo.kodyparton.com`, `ping: 192.168.178.1`) once both NPM proxy hosts existed. Both `ping` checks verified live via `/api/ping` (UNAS 11.8ms, Ziggo 0.9ms).
- `2026-08-30` — Dashboard expansion + visual theme. Added the **UNAS Pro admin console** (`https://192.168.178.38`, UniFi OS 4.0.3) under a new **Network & Storage** group, with a live ICMP reachability card — deliberately the NAS whose blips take down every CIFS-mounted container. Moved Nginx Proxy Manager and AdGuard Home into that group. Enabled three no-credential widgets: **Open-Meteo weather** (Haarlem, no API key, unlike OpenWeatherMap), **datetime** pinned to `Europe/Amsterdam`, and **Uptime Kuma** via its public status page. Corrected the resources widget from the meaningless VM overlay to the real Mac boot disk, and added `uptime`. Added `custom.css` (glass cards, animated gradient, glowing status dots, `prefers-reduced-motion` respected) and tracked it in git. Added `Personal` to the layout, where it had been missing. Staged six credential-gated widgets as commented blocks with `.env.example` entries.
- `2026-08-24` — Doc created. Added Vikunja to the dashboard. Began internal-URL setup (DNS + NPM steps still pending).
- `2026-08-17` — Built as Heimdall's replacement.
