# Single Sign-On (Authelia)

Deployed 2026-08-26. Authelia is the homelab's OIDC identity provider, currently serving Immich, Paperless-ngx, and Vaultwarden.

## Current status (updated 2026-08-30)

`auth.kodyparton.com` resolves and serves a valid discovery document — the two blocking steps described further down were completed in an earlier session and that section is retained only as history. **Immich SSO is live as of 2026-08-30.**

| Service | Local login | SSO status |
|---|---|---|
| Immich | ✅ still on (deliberate fallback) | ✅ **ACTIVE 2026-08-30** — "Login with Authelia" button live, full handshake verified |
| Paperless-ngx | ✅ works (`kody` superuser, pw in Infisical) | ✅ **ACTIVE 2026-08-30** — "Authelia SSO" button live, handshake verified |
| Vaultwarden | ✅ works | ⬜ pre-configured, **not enabled**. ⚠️ Its client has the *same latent redirect_uri bug* — only `http://192.168.178.69:30040/identity/connect/oidc-signin` is registered, no `https://vault.kodyparton.com` equivalent. Fix that at the same time SSO is turned on, or it will fail identically. Local login stays on permanently. |

### The redirect_uri trap — hit twice, and still armed once

Every OIDC client in this stack was registered **before** its app was reachable through NPM, so each one lists only a raw-IP `http://192.168.178.69:<port>/...` callback. The moment you log in from the public hostname, Authelia rejects the callback with `invalid_redirect_uri`. This bit Immich and Paperless on consecutive attempts, and Vaultwarden's client is still in that state.

It presents as "SSO is broken" rather than "one URI is missing", which is what makes it expensive to diagnose. When wiring any new client:

1. Register the **https** callback in Authelia (keep the IP one for direct LAN access — they coexist fine).
2. Make sure the *app's own* notion of its base URL matches. Paperless builds its callback from `PAPERLESS_URL`; Immich builds its from the browser origin. If the app thinks it lives at an IP, it will send an IP callback no matter what Authelia allows.
3. Verify by driving a real authorization request and **also** driving a deliberately bogus one. If the bogus URI is *not* rejected, your test proves nothing.

### Enabling Immich SSO — what it actually took

Run with `scripts/enable_immich_sso.py` (reads `OIDC_CLIENT_SECRET_IMMICH` and `IMMICH_ADMIN_PASSWORD` from Infisical, does a read-modify-write on Immich's live system config so an upgrade's new keys are never clobbered).

**The part that would have silently broken it:** the Authelia client's `redirect_uris` listed only `http://192.168.178.69:30042/...` — the raw IP over http, from before Immich was reachable through NPM. A browser login from `https://photos.kodyparton.com` would have failed at the callback with `invalid_redirect_uri`. The https URIs were added (IP ones kept for direct LAN access, which still works).

Settings chosen, and why:

- `autoRegister: true` is safe **only because** the Authelia account `kody` carries the same email as the existing Immich admin (`the admin's Gmail address`, checked on both sides first). The first SSO login therefore links to that admin account rather than quietly creating a second, non-admin user.
- `autoLaunch: false` on purpose. With it on, the login page bounces straight to Authelia — if SSO ever breaks you are locked out of your own library with no way back to the password form.
- `passwordLogin` stays **enabled** as the escape hatch, for the same reason.
- `profileSigningAlgorithm: none` and `tokenEndpointAuthMethod: client_secret_post` mirror the Authelia client's `userinfo_signed_response_alg: 'none'` and `token_endpoint_auth_method: 'client_secret_post'`. PKCE (S256) is required by the client and Immich sends it.

**Verified, not assumed:** `/api/server/features` reports `oauth: true`; Immich's `/api/oauth/authorize` produces a correct PKCE authorization URL; and Authelia answers that URL with a `302` into its own login flow (`flow_id` issued) rather than an error — which is what proves the client_id, redirect_uri and PKCE challenge were all accepted.

## Why Authelia needs a real hostname

Authelia validates the `Host` header against its configured session cookie domain, and cookie domains cannot be IP addresses. Hitting it directly returns `400 Bad Request`:

```
curl http://localhost:30039/.well-known/openid-configuration    -> 400
curl -H "Host: auth.kodyparton.com" \
     -H "X-Forwarded-Proto: https" ...                          -> 200 ✅
```

That second form is exactly what NPM sends, so this is purely a "needs to be behind the proxy" constraint, not a misconfiguration. Verified working — the discovery document returns correct endpoints under the right hostname.

## (historical) What was blocking — RESOLVED

Both steps below are **done**; `auth.kodyparton.com` has been working since. Kept for the reasoning, not as an action list:

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
