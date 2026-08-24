# n8n

Workflow automation engine — hosts every automation described in `docs/architecture/automation.md`: monitoring, self-healing, digests, and integrations across this stack and external services.

## Quick Facts

| | |
|---|---|
| **Image** | `docker.n8n.io/n8nio/n8n` |
| **Container name** | `n8n-n8n-1` (no explicit `container_name` set, so compose derives it from the project+service name) |
| **Compose file** | `n8n/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `5678:5678` |
| **Local URL** | `http://192.168.178.69:5678` |
| **Public URL** | `https://n8n.kodyparton.com` (via NPM) |
| **PUID/PGID** | n/a |
| **Timezone** | `${GENERIC_TIMEZONE}` → `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `n8n_data` (named volume) | `/home/node/.n8n` | workflows, credentials, execution history — the actual database | not a bind mount, lives in Docker's own volume storage |
| `n8n/local-files` | `/files` | file passthrough for workflows that read/write files | currently unused |

## Dependencies

- **Depends on:** SSH access to the host (`Mac Mini SSH` credential) for most ops workflows; direct HTTP to every other service's API for the rest.
- **Depended on by:** nothing internal, but it's the automation layer for the whole stack — see `docs/architecture/automation.md` for the full map.

## Credentials & Secrets

- Owner account: email `kody.m.parton@gmail.com`, password set at provisioning time (2026-08-17), not tracked anywhere in this repo.
- `n8n/.env` (gitignored) holds `SUBDOMAIN=n8n`, `DOMAIN_NAME=kodyparton.com`, `GENERIC_TIMEZONE=America/Chicago` — these feed `N8N_HOST`/`WEBHOOK_URL` in compose. `.env.example` is the committed template.
- All per-service API keys used by workflows live as proper n8n credential objects (Settings → Credentials), not hardcoded in workflow JSON — see `docs/architecture/automation.md` for the full credential list.

## External Access

NPM proxy host `n8n.kodyparton.com` → `192.168.178.69:5678`, SSL forced. Was previously misrouted to a dead host (`10.10.1.5:30065`, leftover from before this migrated to Docker Compose); fixed 2026-08-17.

## Backups

Its own workflows/credentials database (`n8n_data` volume) isn't currently covered by `scripts/backup_check.sh` — worth adding if workflow loss would be costly (it would be: this now represents significant configuration work).

## Automation

n8n hosts the automation — see `docs/architecture/automation.md` for the complete workflow-by-workflow map rather than duplicating it here.

## Known Issues / Gotchas

- **Broken on first deploy (fixed 2026-08-17):** `compose.yml` referenced `${SUBDOMAIN}`/`${DOMAIN_NAME}`/`${GENERIC_TIMEZONE}` with no `.env` file supplying them, so it booted with `N8N_HOST=.` and a broken webhook URL. Fixed by adding the `.env`.
- **API key permissions:** the n8n public API key used for programmatic workflow management can create/read/update/list workflows and credentials, but **cannot activate workflows** — n8n's public API deliberately restricts that. Every workflow built via the API lands `active: false` and needs a manual toggle in the UI after its credentials are filled in. This is a real n8n platform limitation, not a bug on our end — and arguably a good forcing function, since several workflows perform real writes (container restarts, approvals, indexer disables) that deserve a human glance before going live.
- Container name has no explicit `container_name:` in compose, unlike almost every other service in this repo — it's `n8n-n8n-1`, derived from `<project>-<service>-<replica>`. Relevant if you're writing an SSH command or drift-check script that assumes the `<dir>-<service>-1` pattern doesn't apply here the same way it does for, say, `nginx-app-1`.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-17` — Fixed missing `.env` (broken `N8N_HOST`), fixed NPM routing to a dead host.
