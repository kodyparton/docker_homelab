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

`paperless/.env` (gitignored): `SECRET_KEY`, `OIDC_CLIENT_SECRET`, `SMTP_PASSWORD`.

**Login:** superuser `kody` (email `the admin's Gmail address`), password in Infisical as `PAPERLESS_ADMIN_PASSWORD` — **verified 2026-08-30 to actually authenticate** (checked against Django's own `check_password`, not assumed). Retrieve with:

```
python3 scripts/infisical_client.py get PAPERLESS_ADMIN_PASSWORD
```

Still worth rotating, but it is not lost.

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
- **`PAPERLESS_URL` is load-bearing for SSO, and this is the trap that broke it.** Paperless derives *both* its Django CSRF/allowed-hosts *and* the OIDC callback URL it registers with the provider from that one variable. It was set to `http://192.168.178.69:30041` (from before Paperless sat behind NPM), so a login from `https://paperless.kodyparton.com` sent Authelia a callback pointing at an http IP address — which Authelia rejected as `invalid_redirect_uri`, and which would have dropped the session and failed CSRF even if it hadn't. Fixed 2026-08-30 to `https://paperless.kodyparton.com`, with `PAPERLESS_ALLOWED_HOSTS` and `PAPERLESS_CSRF_TRUSTED_ORIGINS` added so direct IP access keeps working (setting `PAPERLESS_URL` alone would have replaced it, not added to it).
- **The callback must match Authelia's registered URI exactly, trailing slash included** — `/accounts/oidc/<provider_id>/login/callback/`, where `<provider_id>` is the `provider_id` in `PAPERLESS_SOCIALACCOUNT_PROVIDERS` (here `authelia`), *not* the client_id.
- **Do not test whether the OIDC secret reached the container by looking for `$OIDC_CLIENT_SECRET` in its environment** — it is not passed as its own variable. Compose substitutes it into `PAPERLESS_SOCIALACCOUNT_PROVIDERS` at parse time, so the env var is legitimately absent inside the container while the secret is present in the JSON. Checking the wrong thing here reads like a broken secret when nothing is wrong.

## Change Log

- `2026-08-30` — **Authelia SSO made to work.** Two changes: `PAPERLESS_URL` corrected from the raw IP to `https://paperless.kodyparton.com` (plus `PAPERLESS_ALLOWED_HOSTS`/`PAPERLESS_CSRF_TRUSTED_ORIGINS` to retain IP access), and the matching https callback added to Authelia's `paperless` client. Verified by driving a real authorization request: the registered callback is accepted (`302` into Authelia's login flow), while a deliberately bogus one is rejected (`invalid_request`) — confirming the check is meaningful rather than vacuous. Also confirmed the vault's `PAPERLESS_ADMIN_PASSWORD` authenticates as `kody`.
- `2026-08-26` — Built with SQLite, throttled workers, OIDC pre-wired.
