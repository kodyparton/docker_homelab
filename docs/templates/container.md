<!--
Template for documenting a single homelab service.
Copy this file to docs/containers/<service>.md and fill it in.
Keep it updated whenever the service's compose.yml, ports, mounts,
credentials, or role in an n8n workflow changes.
-->

# <Service Name>

One or two sentences: what this service is and why it's in the stack.

## Quick Facts

| | |
|---|---|
| **Image** | `<registry>/<image>:<tag>` |
| **Container name** | `<name>` |
| **Compose file** | `<path>/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `<host>:<container>` |
| **Local URL** | `http://192.168.178.69:<port>` |
| **Public URL** | `https://<subdomain>.kodyparton.com` (via NPM) or _none_ |
| **PUID/PGID** | `1000/1000` (linuxserver images) or _n/a_ |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` / `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `<host path>` | `<container path>` | config / media / etc. | e.g. "SMB share, see known issue #1" |

## Dependencies

- **Depends on:** other services this one needs to function (e.g. Prowlarr needs indexers configured; Sonarr needs qBittorrent as a download client).
- **Depended on by:** other services/workflows that call into this one.

## Credentials & Secrets

Where the API key / password / token lives, and how it's referenced elsewhere (env var name, n8n credential name, etc.). Never put the actual secret value in this file.

## External Access

Nginx Proxy Manager proxy host entry (if any): domain → forward host:port, SSL forced y/n. If not exposed publicly, say so explicitly.

## Backups

What's backed up, where the backup files land, how often, and what (if anything) verifies them (e.g. `scripts/backup_check.sh` via n8n workflow 03).

## Automation

Which n8n workflows read from, write to, or monitor this service. Link by workflow name and number, e.g. "01 - Certificate & Domain Expiry Monitor".

## Known Issues / Gotchas

Anything non-obvious a future reader (including future-you) would want to know before touching this service.

## Change Log

- `YYYY-MM-DD` — what changed and why.
