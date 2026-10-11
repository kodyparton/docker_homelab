# Uptime Kuma

Self-hosted uptime/status monitoring (MIT licensed) with history — added 2026-08-26 to fill a real gap found during a stack review: this homelab already has failure *alerting* (workflow 27 checks the second brain every 15min, workflow 17's `!status` gives a live snapshot), but nothing gives a visual "here's 30 days of uptime %" view for anything. Complements the existing Discord-based alerting rather than replacing it.

## Quick Facts

| | |
|---|---|
| **Image** | `louislam/uptime-kuma:1` |
| **Container name** | `uptime-kuma` |
| **Compose file** | `uptime-kuma/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30038:3001` |
| **Local URL** | `http://192.168.178.69:30038` |
| **Public URL** | `https://uptime.kodyparton.com` (NPM proxy host exists and is enabled; LAN-resolved via AdGuard) |
| **PUID/PGID** | n/a |
| **Timezone** | `Europe/Amsterdam` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `uptime-kuma/data` | `/app/data` | SQLite DB — all monitors, history, admin account | gitignored (matches `*/data/` pattern) |

## Dependencies

- **Depends on:** DNS resolution of `*.kodyparton.com` to `192.168.178.69` (AdGuard Home) and NPM to terminate TLS — every monitor targets a public DNS name rather than a `host:port`, so both must be healthy or the monitors all report down together.
- **Depended on by:** Homepage's `uptimekuma` widget, which reads the **public status page**, not the admin API — which is why that widget needs no credential.

## Credentials & Secrets

First-run admin account creation happens via the web UI, same as Vikunja/Trilium/Infisical — deliberately not self-served.

## External Access

Not exposed via NPM. LAN-only.

## Backups

Not yet wired into workflow 03. Low priority relative to Infisical's backup (this data is regenerable status history, not irreplaceable secrets), but worth adding if it ends up mattering.

## Automation

`scripts/kuma_seed_monitors.sh` seeds one HTTP monitor per public DNS name (25 of them, the full NPM proxy-host list — 23 containers plus the UNAS Pro and Ziggo modem appliances; `comics.kodyparton.com` → Komga added 2026-10-11 and **not seeded yet**) and publishes them to a status page.

Uptime Kuma v1 has **no REST API for monitor CRUD** — it is Socket.IO only — so the script runs `node` *inside the container*, which already ships `socket.io-client`. Nothing is installed on the host to make this work.

- **Password handling:** environment → Infisical (`KUMA_ADMIN_PASSWORD`) → interactive prompt, passed only through the `docker exec` environment. Never in argv (visible in `ps`), never written to disk. `KUMA_TOTP=<code>` if 2FA is on. Unlike `NPM_ADMIN_PASSWORD` and `ADGUARD_ADMIN_PASSWORD`, Kuma's password is **not** in Infisical yet, so this normally prompts — store it to make the script unattended.
- **`NODE_PATH=/app/node_modules` is required** — the script is dropped in `/tmp`, so Node's default resolution never walks up to where `socket.io-client` lives.
- **Idempotent:** monitors are matched by name, so re-running adds only what is missing. `DRY_RUN=1` to preview; `KUMA_STATUS_PAGE=0` for monitors without a status page.

## Known Issues / Gotchas

- **Monitors must accept `200-399`, not Kuma's `200-299` default.** Five hosts answer a bare `GET /` with a redirect to a login page — `books` 303, `dns` 302, `paperless` 302, `request` 307, `uptime` 302 (all measured from inside the container, not assumed). Under the default range those five would report down permanently while being perfectly healthy. The seed script sets this correctly.
- **A nonexistent status page slug returns HTTP 200 with empty lists, not a 404.** `/api/status-page/heartbeat/<anything>` answers `{"heartbeatList":{},"uptimeList":{}}` for a slug that was never created. This is genuinely misleading: it makes a missing status page look like an existing-but-empty one. Confirm against the DB (`SELECT slug FROM status_page`) rather than trusting the endpoint.
- **Monitoring `uptime.kodyparton.com` from Uptime Kuma itself is near-useless** — if Kuma is down, nothing is left to record the outage. It is included for completeness of the list, but real coverage of Kuma needs an external checker.
- TLS verification is left **on** for all monitors; the NPM wildcard cert is valid and verified from inside the container.

## Change Log

- `2026-10-11` — Added `comics.kodyparton.com` (labelled **Komga**; briefly YACReader the same day) to `kuma_seed_monitors.js`. Not seeded: the script needs `KUMA_ADMIN_PASSWORD`, which isn't in Infisical, so run `bash scripts/kuma_seed_monitors.sh` interactively.
- `2026-08-30` (later) — Added `UNAS Pro` and `Ziggo Modem` monitors to the seed list (24 total) and an Infisical lookup for the admin password.
- `2026-08-30` — Added `scripts/kuma_seed_monitors.sh` + `.js` to seed 22 HTTP monitors (one per NPM proxy host) by DNS name, plus a published status page at `/status/default` so Homepage's widget has something to read. Corrected the doc's stale `America/Chicago` timezone and the "no public URL" claim. Documented the `200-399` accepted-status requirement and the misleading empty-200 status-page endpoint.
- `2026-08-26` — Built, during a stack-wide redundancy/optimization review. Admin account creation left to the user.
