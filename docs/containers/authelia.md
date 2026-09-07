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
- ~~No SMTP configured~~ — **fixed 2026-08-29**. Now sends real password-reset/2FA-enrolment emails via Gmail SMTP relay (app password, `AUTHELIA_NOTIFIER_SMTP_PASSWORD` in gitignored `authelia/.env`, value sourced from Infisical's `Homelab_SMTP` secret). Config lives in `authelia/config/configuration.yml`'s `notifier.smtp` block. Verified: clean startup with no config errors, container healthy. The old filesystem-notifier fallback (`/data/notification.txt`) is gone — if this ever breaks again (e.g. Google revokes the app password), Authelia will fail to send rather than silently falling back, so check `docker logs authelia` if resets stop arriving.
- `chown: /config/...: Read-only file system` appears at startup — harmless, caused by the deliberate read-only config mount.

## Change Log

- `2026-08-30` — Added `https://paperless.kodyparton.com/accounts/oidc/authelia/login/callback/` to the `paperless` client's `redirect_uris` (IP one kept). Same root cause as the Immich fix the same day. **The `vaultwarden` client still has this bug latent** — only its IP callback is registered; fix when its SSO is enabled.

- `2026-08-30` — Added `https://photos.kodyparton.com/auth/login` and `/user-settings` to the `immich` OIDC client's `redirect_uris`. They had only ever listed the raw-IP http URIs from before Immich was proxied, so an SSO login from the public hostname would have failed at the callback with `invalid_redirect_uri`. IP URIs kept for direct LAN access. Immich SSO went live the same day.

- `2026-08-26` — Built. OIDC clients configured for Immich, Paperless, Vaultwarden.
