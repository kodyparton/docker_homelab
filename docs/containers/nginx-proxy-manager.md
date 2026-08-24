# Nginx Proxy Manager (NPM)

Reverse proxy and TLS termination for every publicly-reachable service in this stack, plus the intended entry point for the new internal-only `home.kodyparton.com` URL.

## Quick Facts

| | |
|---|---|
| **Image** | `jc21/nginx-proxy-manager:latest` |
| **Container name** | `nginx-app-1` (no explicit `container_name`) |
| **Compose file** | `nginx/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `80`, `443` (public), `81` (admin UI) |
| **Local URL** | Admin: `http://192.168.178.69:81` |
| **Public URL** | n/a — it *is* the thing that provides public URLs to everything else |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `nginx/data` | `/data` | proxy host configs, generated nginx confs, sqlite database, logs | gitignored — contains a live Cloudflare API token, see Credentials below |
| `nginx/letsencrypt` | `/etc/letsencrypt` | issued TLS certificates | gitignored |

## Dependencies

- **Depends on:** Cloudflare (DNS-01 challenge for certs), the LAN IP/port of every service it proxies.
- **Depended on by:** n8n, Overseerr, qBittorrent (intended), Homepage (intended, once `home.kodyparton.com` is finished) reach the outside world through here.

## Credentials & Secrets

- Admin login: not tracked in this repo.
- **A Cloudflare API token with DNS edit rights lives in plaintext inside `nginx/data/database.sqlite`** (`certificate.meta.dns_provider_credentials`), used for automatic DNS-01 cert renewal of `*.kodyparton.com`. This is NPM's own normal operation, not something this repo introduced, but it's worth knowing that token exists and has real write access to the domain's DNS if `nginx/data` is ever exposed.

## External Access

n/a (this is the access layer itself).

## Backups

Not currently covered by `scripts/backup_check.sh`. `nginx/data/database.sqlite` holds all proxy host + cert configuration — losing it would mean recreating every routing rule by hand. Worth adding to backup coverage.

## Automation

None directly — no n8n workflow currently reads/writes NPM. Its `proxy_host` table has been read (not written) via direct sqlite queries during troubleshooting sessions, documented in `docs/architecture/known-issues.md`.

## Known Issues / Gotchas

- **Direct database/config writes to this container are deliberately avoided**, even for read-only-adjacent fixes, after a safety check flagged automated writes to shared production routing infrastructure as needing explicit human action. Two proxy host entries have needed fixing so far (see `docs/architecture/known-issues.md` for the full list) — both were done as *manual* NPM UI steps, not automated.
- **`downloads.kodyparton.com` still routes to a dead host** (`10.10.0.130:30024`) as of this doc's last update — not yet fixed. See `qbittorrent.md` and `docs/architecture/known-issues.md`.
- Its actual routing is driven by generated `.conf` files in `/data/nginx/proxy_host/<id>.conf` inside the container, which are only created/updated by NPM's own backend when you save a proxy host through its UI or API — the sqlite `proxy_host` table alone is not sufficient to make a route live.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-17` — Fixed n8n's proxy host (was pointed at a dead host `10.10.1.5:30065`).
