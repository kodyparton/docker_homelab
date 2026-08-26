# Paperless-ngx

Document management with OCR — scan or drop in bills, warranties, tax documents, and they become full-text searchable.

## Quick Facts

| | |
|---|---|
| **Image** | `ghcr.io/paperless-ngx/paperless-ngx:latest` + `redis:7-alpine` |
| **Container name** | `paperless`, `paperless-redis` |
| **Compose file** | `paperless/compose.yml` |
| **Port(s)** | `30041:8000` |
| **Local URL** | `http://192.168.178.69:30041` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `paperless/consume` | `/usr/src/paperless/consume` | **drop documents here to import them** | gitignored |
| `paperless/media` | `/usr/src/paperless/media` | stored originals + archived PDFs | gitignored |
| `paperless/data` | `/usr/src/paperless/data` | SQLite DB, search index | gitignored |
| `paperless/export` | `/usr/src/paperless/export` | export target | gitignored |

## Dependencies

- **Depends on:** its own Redis (internal). Optionally Authelia for SSO.
- **Depended on by:** nothing yet — though its REST API is a natural fit for the second brain answering questions like "when does the dishwasher warranty expire?"

## Credentials & Secrets

`paperless/.env` (gitignored): `SECRET_KEY`, `OIDC_CLIENT_SECRET`. Superuser `kody`; password in Infisical as `PAPERLESS_ADMIN_PASSWORD` — **change it**.

## External Access

None currently. LAN only.

## Backups

Not yet wired into workflow 03. `paperless/media` holds the only copy of imported originals — worth backing up before relying on it. Paperless has a built-in `document_exporter` management command suited to this.

## Automation

None yet.

## Known Issues / Gotchas

- **Runs on SQLite, not Postgres** — deliberate. Paperless' own docs recommend SQLite for low-resource hosts, and this box shares RAM with Ollama. If the document count ever grows into the tens of thousands, revisit.
- Workers are capped (`WEBSERVER_WORKERS=2`, `TASK_WORKERS=1`) so OCR doesn't monopolise CPU that Ollama needs. OCR will be slower than a dedicated machine — bursty load, so far friendlier than Immich's continuous ML.
- Local login is intentionally left enabled alongside SSO so the superuser can always get in.

## Change Log

- `2026-08-26` — Built with SQLite, throttled workers, OIDC pre-wired.
