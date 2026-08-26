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
| **Public URL** | _none_ — LAN only for now |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `uptime-kuma/data` | `/app/data` | SQLite DB — all monitors, history, admin account | gitignored (matches `*/data/` pattern) |

## Dependencies

- **Depends on:** nothing — it just makes outbound HTTP/TCP/ping checks against whatever monitors get configured.
- **Depended on by:** nothing yet.

## Credentials & Secrets

First-run admin account creation happens via the web UI, same as Vikunja/Trilium/Infisical — deliberately not self-served.

## External Access

Not exposed via NPM. LAN-only.

## Backups

Not yet wired into workflow 03. Low priority relative to Infisical's backup (this data is regenerable status history, not irreplaceable secrets), but worth adding if it ends up mattering.

## Automation

None yet — monitors need to be configured by hand via the web UI (Uptime Kuma v1 doesn't have a simple REST API for monitor management, it's Socket.IO-based, so scripting monitor creation is more involved than the REST-API pattern used for everything else in this repo).

## Known Issues / Gotchas

None yet — just deployed, no monitors configured.

## Change Log

- `2026-08-26` — Built, during a stack-wide redundancy/optimization review. Admin account creation left to the user.
