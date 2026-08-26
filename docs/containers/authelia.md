# Authelia

SSO / OIDC identity provider for the homelab. Chosen over Authentik specifically for resource reasons: <35MB RAM vs Authentik's 2GB+ requirement, on a host where Ollama already claims ~5GB of a 12GB VM. Its file-based declarative config also matches how the rest of this repo works.

## Quick Facts

| | |
|---|---|
| **Image** | `authelia/authelia:latest` (v4.39.20 at deploy) |
| **Container name** | `authelia` |
| **Compose file** | `authelia/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30039:9091` |
| **Local URL** | `http://192.168.178.69:30039` — **returns 400 by design**, see below |
| **Public URL** | `https://auth.kodyparton.com` — **not yet created, required for SSO to work** |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `authelia/config` | `/config` (ro) | configuration.yml, users_database.yml, oidc.key | mounted read-only; `configuration.yml` is git-tracked, the other two are not |
| `authelia/data` | `/data` | SQLite DB, notification.txt | gitignored |

## Dependencies

- **Depends on:** Nginx Proxy Manager — genuinely required, not optional. Authelia rejects requests whose `Host` doesn't match its cookie domain, and cookie domains can't be IPs.
- **Depended on by:** Immich, Paperless-ngx, Vaultwarden (all OIDC clients).

## Credentials & Secrets

`authelia/.env` (gitignored): `JWT_SECRET`, `SESSION_SECRET`, `STORAGE_ENCRYPTION_KEY`, `OIDC_HMAC_SECRET`. User login password is in Infisical as `AUTHELIA_KODY_PASSWORD`. Per-app OIDC client secrets are in Infisical; Authelia itself stores only argon2id digests of them.

## External Access

Not yet. Needs a Cloudflare DNS record (DNS-only) + NPM proxy host — see `docs/architecture/sso.md`.

## Backups

Not yet wired into workflow 03. `authelia/data/db.sqlite3` holds 2FA enrolments and sessions; `config/oidc.key` is the more critical item and is not backed up anywhere — regenerating it would invalidate all existing OIDC sessions.

## Automation

None yet.

## Known Issues / Gotchas

- **`http://192.168.178.69:30039` returns `400 Bad Request`. This is correct behaviour, not a fault** — Authelia validates the Host header. It works when reached via `auth.kodyparton.com` through NPM (verified with forwarded headers).
- No SMTP configured: password-reset and 2FA-enrolment emails write to `/data/notification.txt` instead of sending. Read with `docker exec authelia cat /data/notification.txt`.
- `chown: /config/...: Read-only file system` appears at startup — harmless, caused by the deliberate read-only config mount.

## Change Log

- `2026-08-26` — Built. OIDC clients configured for Immich, Paperless, Vaultwarden.
