# Vaultwarden

Bitwarden-compatible password manager for **human logins** — browser autofill, 2FA seeds, secure notes. Complements Infisical rather than duplicating it: Infisical holds API keys and service secrets, Vaultwarden holds the passwords you personally type.

## Quick Facts

| | |
|---|---|
| **Image** | `vaultwarden/server:latest` |
| **Container name** | `vaultwarden` |
| **Compose file** | `vaultwarden/compose.yml` |
| **Port(s)** | `30040:80` |
| **Local URL** | `http://192.168.178.69:30040` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `vaultwarden/data` | `/data` | SQLite DB, attachments, RSA keys | gitignored — **this is the vault** |

## Dependencies

- **Depends on:** nothing hard. Authelia for SSO, but see below — that dependency is deliberately soft.
- **Depended on by:** nothing.

## Credentials & Secrets

`vaultwarden/.env` (gitignored): `ADMIN_TOKEN` (stored as an argon2id PHC hash, not plaintext), `OIDC_CLIENT_SECRET`. Both also in Infisical.

`SIGNUPS_ALLOWED=false` — accounts are created deliberately via the `/admin` panel, not by anyone who can reach the LAN.

## External Access

None currently. LAN only. Note: browser extensions and mobile apps generally require HTTPS, so real-world use will likely need this behind NPM.

## Backups

**Not yet configured, and this is the highest-stakes gap of the four new services** — `vaultwarden/data` is the vault itself. Losing it loses every stored password. Should be backed up before it holds anything real.

## Automation

None yet.

## Known Issues / Gotchas

- **SSO is enabled but local login is deliberately kept on** (`SSO_ONLY=false`). Putting a password manager fully behind SSO creates a circular dependency — if Authelia breaks, you can't reach the vault that may hold the credentials to fix it. This was an explicit decision; don't "clean it up" by enabling SSO-only.
- Vaultwarden's own `vaultwarden hash` command needs an interactive TTY and can't be piped; the admin token hash here was generated with Authelia's argon2 tool using matching Bitwarden parameters (argon2id, m=65536, t=3, p=4).
- SSO requires Vaultwarden 1.36.0+ (official support, no longer a fork).

## Change Log

- `2026-08-26` — Built. Admin token hashed, signups disabled, SSO wired with local login retained.
