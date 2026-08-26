# Single Sign-On (Authelia)

Deployed 2026-08-26. Authelia is the homelab's OIDC identity provider, currently serving Immich, Paperless-ngx, and Vaultwarden.

## ⚠️ Current status: built and working, but SSO is not active yet

Authelia itself is running and its OIDC provider is verified functional. **But it cannot be used until `auth.kodyparton.com` exists**, and that needs two manual steps only you can do (see "What's blocking" below).

Everything is deliberately built so this isn't a blocker for using the apps:

| Service | Local login today | SSO once DNS is done |
|---|---|---|
| Immich | ✅ works now | pre-configured, needs enabling in its admin UI |
| Paperless-ngx | ✅ works now (`kody` superuser) | pre-configured in compose |
| Vaultwarden | ✅ works now | pre-configured, **local login stays on permanently** |

## Why Authelia needs a real hostname

Authelia validates the `Host` header against its configured session cookie domain, and cookie domains cannot be IP addresses. Hitting it directly returns `400 Bad Request`:

```
curl http://localhost:30039/.well-known/openid-configuration    -> 400
curl -H "Host: auth.kodyparton.com" \
     -H "X-Forwarded-Proto: https" ...                          -> 200 ✅
```

That second form is exactly what NPM sends, so this is purely a "needs to be behind the proxy" constraint, not a misconfiguration. Verified working — the discovery document returns correct endpoints under the right hostname.

## What's blocking (manual steps for you)

Same pattern as `home.kodyparton.com`, still outstanding from an earlier session:

1. **Cloudflare DNS**: add `auth.kodyparton.com`. Set it **DNS only (not proxied)** pointing at the LAN IP, matching the `home.kodyparton.com` approach — this keeps it internal-only, which is right for an identity provider.
2. **NPM proxy host**: `192.168.178.69:81` → Hosts → Proxy Hosts → Add:
   - Domain: `auth.kodyparton.com`
   - Forward to: `192.168.178.69` port `30039`
   - **Enable "Websockets Support"**
   - SSL tab: use the existing `*.kodyparton.com` wildcard cert, **Force SSL on**

Why manual: direct writes to NPM's database have been blocked before as production-infra changes that should go through its own UI (see `known-issues.md`), and Cloudflare needs the account owner regardless.

Once both are done, `https://auth.kodyparton.com` should show a login page, and SSO buttons in the three apps will start working.

## Design decisions worth knowing

### Vaultwarden keeps local login — permanently, on purpose
Putting a password manager fully behind SSO creates a circular dependency: if Authelia breaks, you can't reach the vault that may hold the credentials needed to fix Authelia. Vaultwarden is configured with `SSO_ENABLED=true` **and** `SSO_ONLY=false`, so email/password login always remains as a break-glass path. This was an explicit decision, not an oversight — don't "tidy it up" later by enabling SSO-only.

### Paperless keeps local login too
`PAPERLESS_DISABLE_REGULAR_LOGIN` is deliberately not set, so the `kody` superuser can always get in even if Authelia is unreachable.

### Config is declarative and git-tracked
`authelia/config/configuration.yml` is committed — the whole auth setup is reviewable and reproducible, matching how the rest of this repo works. Its OIDC client secrets are stored as **argon2id digests of 48-character random strings**, which is safe to publish by design (that's why Authelia stores digests rather than plaintext).

**Deliberately NOT committed**, since this repo is public:
- `authelia/config/oidc.key` — the RSA private key that signs tokens.
- `authelia/config/users_database.yml` — user password hashes. Even though the current password is random, a hash of a human-chosen password is an offline-cracking target, and you'll likely change it to something memorable.
- All `.env` files.

### Access control
`default_policy: deny`, with `*.kodyparton.com` requiring `one_factor`. Authelia's own domain is `bypass` (otherwise you can't reach the login page to log in). 2FA (TOTP) is available and can be raised to `two_factor` per-domain once you've enrolled a device.

## Credentials

All in Infisical (`Homelab Secrets` / `prod`):

| Secret | What |
|---|---|
| `AUTHELIA_KODY_PASSWORD` | Your Authelia login — **change this** |
| `PAPERLESS_ADMIN_PASSWORD` | Paperless `kody` superuser — **change this** |
| `VAULTWARDEN_ADMIN_TOKEN` | Vaultwarden `/admin` panel (stored hashed in its env) |
| `OIDC_CLIENT_SECRET_IMMICH` / `_PAPERLESS` / `_VAULTWARDEN` | Per-app OIDC client secrets |
| `IMMICH_DB_PASSWORD`, `PAPERLESS_SECRET_KEY` | App internals |
| `PLEX_TOKEN` | Added earlier for the Plex cleanup work |

## Adding a user later

```bash
docker run --rm authelia/authelia:latest \
  authelia crypto hash generate argon2 --password 'their-password'
```
Add them to `authelia/config/users_database.yml` with the resulting digest, put them in a group, then `docker compose restart` in `authelia/`. Groups (`admins`, `family`) are referenced by `access_control` rules — `family` exists in the schema but has no rules yet; add them when someone actually needs scoped access.

## Verification done at build time

- Authelia v4.39.20 starts clean, storage schema migrated 0→24, no config warnings.
- OIDC discovery returns correct issuer/authorization/token/userinfo/JWKS endpoints under the proper hostname.
- All four containers healthy; Ollama confirmed still responding afterwards (the real regression risk on this shared-CPU host).
- Total memory with everything running including a loaded Ollama model: **7.7GB of 12GB**.
