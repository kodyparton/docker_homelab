# Vikunja

Task and project management app — tracks homelab-related tasks and to-dos (including ones surfaced by Claude while working in this repo).

## Quick Facts

| | |
|---|---|
| **Image** | `vikunja/vikunja` (all-in-one image: API + frontend + Caddy in one container) |
| **Container name** | `vikunja` |
| **Compose file** | `vikunja/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30037:3456` |
| **Local URL** | `http://192.168.178.69:30037` |
| **Public URL** | none yet — candidate for a future NPM entry if wanted |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `vikunja/config` | `/db` | SQLite database (`vikunja.db`) | gitignored |
| `vikunja/files` | `/app/vikunja/files` | uploaded attachments | gitignored |

## Dependencies

- **Depends on:** nothing internal.
- **Depended on by:** nothing yet — a natural future candidate for n8n integration (it has a full REST API) if task-creation ever gets automated (e.g. auto-file a task when a workflow finds something that needs manual follow-up).

## Credentials & Secrets

`vikunja/.env` (gitignored) holds `VIKUNJA_JWT_SECRET`, a randomly generated persistent secret (`openssl rand -hex 32`) used to sign session tokens — set explicitly rather than left to auto-generate, since an ephemeral secret would invalidate every session on each container restart. `.env.example` is the committed placeholder template. First-run account creation happens through its own web UI (no default admin credentials were set by this deployment).

## External Access

Not yet exposed via NPM — LAN-only for now.

## Backups

Not yet covered by `scripts/backup_check.sh` — worth adding once real task data accumulates.

## Automation

None yet.

## Known Issues / Gotchas

- Deployed 2026-08-24; used the non-deprecated `VIKUNJA_SERVICE_SECRET` env var rather than the older `VIKUNJA_SERVICE_JWTSECRET` (which still works but logs a deprecation warning and is slated for removal in a future Vikunja release).

## Change Log

- `2026-08-24` — Deployed.
