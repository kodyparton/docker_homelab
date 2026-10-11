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

- Admin login: `NPM_ADMIN_EMAIL` / `NPM_ADMIN_PASSWORD` in Infisical as of 2026-08-29 (added specifically to let automation use NPM's own REST API — see Automation below).
- **A Cloudflare API token with DNS edit rights lives in plaintext inside `nginx/data/database.sqlite`** (`certificate.meta.dns_provider_credentials`), used for automatic DNS-01 cert renewal of `*.kodyparton.com`. This is NPM's own normal operation, not something this repo introduced, but it's worth knowing that token exists and has real write access to the domain's DNS if `nginx/data` is ever exposed.

## External Access

n/a (this is the access layer itself).

## Backups

Not currently covered by `scripts/backup_check.sh`. `nginx/data/database.sqlite` holds all proxy host + cert configuration — losing it would mean recreating every routing rule by hand. Worth adding to backup coverage.

## Automation

None recurring (no n8n workflow reads/writes NPM on a schedule). Its `proxy_host` table has been read directly via sqlite for audits (read-only is fine). As of 2026-08-29, 17 proxy hosts were created in one pass via **NPM's own REST API** (`POST /api/tokens` to authenticate as the admin, then `POST /api/nginx/proxy-hosts`) — this is the supported, non-raw-DB way to write to NPM, distinct from the direct-sqlite-write concern below.

## Known Issues / Gotchas

- **`nas.kodyparton.com` and `ziggo.kodyparton.com` are the only proxy hosts with `https` upstreams, and the only ones not pointing at the Mac Mini.** They forward to the UniFi UNAS Pro (`https://192.168.178.38:443`) and the Ziggo cable modem (`https://192.168.178.1:443`). Three things make them different from every other row, all verified rather than assumed:
  - Both present **self-signed** certificates (`CN=unifi.local`, `CN=OFW-UI-RootCA`). nginx defaults `proxy_ssl_verify` to `off` so this works out of the box, but the proxy host states it explicitly (along with `proxy_ssl_server_name on` for SNI and `proxy_buffering off`) rather than depending on a default. Client-facing TLS is untouched — browsers still get the real wildcard cert.
  - `http://192.168.178.38` **301-redirects to https**, so an `http` upstream cannot work for the UNAS at all — the same behaviour that made Homepage's `siteMonitor` unusable against it (see `homepage.md`). The modem *does* serve plain http (identical 415-byte body, measured), but is proxied over https anyway so its admin credentials are not sent in the clear across the LAN.
  - `allow_websocket_upgrade` is **required** — the UniFi OS console is a websocket-driven SPA and will load but not function without it. Enabled for the modem too, on the same reasoning.
- **If either console loads but login fails**, the usual cause is the appliance rejecting the request's `Origin`/`Referer` because they carry the proxied hostname rather than its own. The fix is to add to that host's advanced config:
  `proxy_set_header Origin https://192.168.178.38;` and `proxy_set_header Referer https://192.168.178.38;`
  (substituting that device's own IP). Not applied pre-emptively: both appliances return `200` to a request bearing a foreign `Host` header (measured), so it may not be needed, and setting these blindly can break other flows.
- **Direct database/config *writes* are still avoided** — the safety concern was specifically about bypassing NPM's own backend (editing `database.sqlite`'s `proxy_host` table directly), not about automation in general. NPM's REST API is the correct, supported path and was used successfully 2026-08-29 to create 17 proxy hosts at once (IDs 6–22) — see `docs/architecture/overview.md`'s domain map for the full list.
- Its actual routing is driven by generated `.conf` files in `/data/nginx/proxy_host/<id>.conf` inside the container, which are only created/updated by NPM's own backend when you save a proxy host through its UI or API — the sqlite `proxy_host` table alone is not sufficient to make a route live. This is exactly why the API (not direct DB writes) is the right tool.

## Change Log

- `2026-08-24` — Doc created.
- `2026-10-11` — Proxy host 25, `comics.kodyparton.com` → `http://192.168.178.69:30044` (YACReader), created by Kody in the UI. Its advanced config was then set through the API to a custom `location /` that sends `Host: $host:$server_port`, because YACReaderLibraryServer 1.8.2 crashes on a bare-hostname `Host` header (see `yacreader.md`). It's the only proxy host that overrides the default location this way. Also turned on HTTP/2 and HSTS, which were off from the UI defaults. With HTTP/2 off, Safari's HTTP/2 connection reuse across the shared wildcard cert gave 421 Misdirected Request. **Any new proxy host needs HTTP/2 on to match the rest.** Login for the API now reads `NPM_ADMIN_EMAIL` from Infisical; `scripts/add_device_proxy_hosts.py`'s default identity is a placeholder since commit f3df75c, so set `NPM_IDENTITY`.
- `2026-10-11` (evening) — Proxy host 25 repointed from YACReader (`:30044`) to **Komga** (`:30045`), which replaced it. The YACReader-only `location /` advanced config was **removed**. Komga needs NPM's standard `Host: $host`, and the `:port` variant would leak into the absolute URLs it builds (OPDS, OAuth2 redirect). HTTP/2 + HSTS stay on. Verified 200 over HTTP/2 with a valid cert.
- `2026-08-30` — Added `nas.kodyparton.com` → `https://192.168.178.38:443` (UniFi UNAS Pro, proxy host 23) and `ziggo.kodyparton.com` → `https://192.168.178.1:443` (Ziggo modem, proxy host 24) via `scripts/add_device_proxy_hosts.py`, which also adds the matching AdGuard rewrites. The only https upstreams in this instance; both reuse wildcard cert id 1. The script pulls `NPM_ADMIN_PASSWORD` from Infisical, falling back to a prompt, and is idempotent — re-running skips hosts that already exist. Both verified end-to-end (`200`, `ssl_verify_result=0`, body byte-identical to direct access).
- `2026-08-17` — Fixed n8n's proxy host (was pointed at a dead host `10.10.1.5:30065`).
- `2026-08-29` — Added `NPM_ADMIN_EMAIL`/`NPM_ADMIN_PASSWORD` to Infisical; created 17 new proxy hosts via the API for services that were previously IP:port-only (password-manager autofill was breaking on raw IPs). Fixed a pre-existing, unrelated Audiobookshelf port-mapping bug (`30033:30033` → `30033:80`, surfaced while verifying its new proxy host).
