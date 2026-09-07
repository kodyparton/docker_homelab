# Infisical

Self-hosted secrets/credential manager (MIT licensed) — the intended home for the API keys, tokens, and passwords currently scattered across per-service `.env` files and n8n's own credential store. Standalone stack: the app itself plus its own Postgres and Redis, all three only reachable from each other unless explicitly port-mapped.

## Quick Facts

| | |
|---|---|
| **Image** | `infisical/infisical:latest-postgres` (app) + `postgres:14-alpine` + `redis:7-alpine` |
| **Container name** | `infisical` (app), `infisical-db`, `infisical-redis` |
| **Compose file** | `infisical/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30034:8080` (app only — db/redis have no host port, internal-only) |
| **Local URL** | `http://192.168.178.69:30034` |
| **Public URL** | _none_ — deliberately LAN-only for now, holds real secrets. Revisit if remote access is ever needed. |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `infisical/data/postgres` | `/var/lib/postgresql/data` | all stored secrets, encrypted at rest | gitignored, this is the actual data — back it up |
| `infisical/data/redis` | `/data` | cache/queue state | gitignored, disposable |

## Dependencies

- **Depends on:** its own Postgres and Redis (bundled in the same compose file, not shared with any other service).
- **Depended on by:** nothing yet — this is the target for a migration, not yet wired into any workflow. Once populated, the intent is for n8n and homelab scripts to pull secrets from here via a machine identity instead of (or in addition to) `.env` files and n8n's built-in credential store.

## Credentials & Secrets

- `infisical/.env` (gitignored): `POSTGRES_PASSWORD`, `ENCRYPTION_KEY` (root encryption key — losing this makes all stored secrets unrecoverable, back it up separately), `AUTH_SECRET` (JWT signing secret).
- The **admin account** (first user, created via the web UI's `/admin/signup` on first run) is the root of trust for the whole store — deliberately not something this second brain / automation self-serves, same reasoning as the Vikunja/Trilium account setup.
- Going forward, programmatic access (for scripts / n8n / rotation) should use an **Infisical Machine Identity** (a scoped service-account-style credential), not the admin account's own login.

## External Access

Not exposed via NPM. LAN-only (`192.168.178.69:30034`) — deliberate, given what it stores. Infisical does have real auth (unlike Ollama/Qdrant's "LAN-only because no auth at all"), so public exposure is more defensible than those if ever needed, but the default here is conservative.

## Backups

Workflow 03 (Backup Verification, daily 09:00) runs `docker exec infisical-db pg_dump -U infisical infisical | gzip` into `infisical/backups/` (gitignored), keeps the last 7, and `scripts/backup_check.sh` alerts if it's missing or older than 2 days. Verified live — a real dump was taken and confirmed readable/valid.

**Still not covered**: the `ENCRYPTION_KEY` in `infisical/.env` itself. A `pg_dump` alone is not enough to restore from — without that specific key, the dump's encrypted secret values are unrecoverable. That key needs its own separate, secure backup (e.g. somewhere outside this repo entirely, like a physical note or a different password manager) — deliberately not something to script into an automated backup alongside the data it protects, since bundling them together would defeat the point of having a separate root key at all.

## Automation

None yet. Planned: a script (`scripts/infisical_*.py`, once a machine identity exists) to read/write secrets programmatically, and a rotation script for whichever homelab credentials support being regenerated via their own API (see `docs/architecture/secrets-and-rotation.md`).

## Known Issues / Gotchas

- The Postgres connection string is a URL (`postgres://user:password@host:port/db`) — if `POSTGRES_PASSWORD` contains `/`, `@`, `:`, `+`, or `=` (e.g. straight `openssl rand -base64` output), it breaks URL parsing and the app fails to boot with `TypeError: Invalid URL`. Use `openssl rand -hex N` for this specific password (hex-only, always URL-safe) — already done here, just don't regenerate it with base64 later without remembering this.
- Self-hosted Community Edition is feature-gated vs. Infisical's paid tiers — confirmed via its own startup log (`"Current license does not support custom rate limit configuration"`). Before relying on any specific advanced feature (their polished "Secret Rotation" UI in particular), verify it's actually available on the free self-hosted tier rather than assuming — see `docs/architecture/secrets-and-rotation.md` for what was actually verified.
- Infisical's own docs claim personal Gmail accounts aren't supported for SMTP ("only Google Workspace / Cloud Identity customers," dated May 2022) — tested directly against this instance with a personal Gmail app password anyway and it worked fine (`SMTP - Verified connection to smtp.gmail.com:587` in the startup log). That docs note appears stale or describes a different, older restriction (likely "less secure apps," which app passwords are Google's own supported workaround for). Don't assume it's a real blocker without testing.
- **2026-08-28/29: Kody got locked out of the web UI admin login** (forgotten password, and there was no reset path — no SMTP configured, no working OAuth). Investigated the account directly: not locked (`isLocked: false`), `superAdmin: true`, real blocker was genuinely the password. Infisical's `infisical bootstrap` CLI command looked promising but is first-run-only (`--ignore-if-bootstrapped` just no-ops on an already-configured instance, it can't reset an existing admin). Considered directly editing `hashedPassword`/`user_encryption_keys` in Postgres, but Infisical's secrets are end-to-end encrypted with a key derived from the *original* password — a raw password reset would let the account log in but likely leave existing secrets undecryptable, which is not reversible after the fact. **Did not attempt that.** Fixed the actual blocker instead (this SMTP setup) so the normal "Forgot password" email flow works — the safe, supported path. The machine identity (`homelab-automation`) used by `scripts/infisical_client.py` for all programmatic access was never affected by any of this; it's a completely separate credential from the personal admin login.

## Change Log

- `2026-08-26` — Built. Admin account creation handed to the user (manual, by design).
- `2026-08-29` — Added Gmail SMTP relay (`SMTP_HOST`/`PORT`/`USERNAME`/`PASSWORD`/`FROM_ADDRESS`/`FROM_NAME` env vars, password in gitignored `infisical/.env`) — enables password-reset emails and was the safe fix for the admin lockout above. Also wired into Authelia's notifier (see `docs/containers/authelia.md` if one exists, or its compose/config directly) using the same `Homelab_SMTP` Infisical secret.
