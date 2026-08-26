# Secrets Store & Rotation

Infisical (`docs/containers/infisical.md`) is now running as the intended central home for this homelab's credentials. This doc covers two separate things people often conflate: **storing** secrets centrally (straightforward, Infisical does this well) and **rotating** them (harder, and honestly assessed per-service below rather than assumed).

## Status as of 2026-08-26

- ✅ Infisical stack running (`infisical/`), Postgres + Redis + app, LAN-only at `192.168.178.69:30034`.
- ✅ Admin account created (by Kody, by design) and a **Machine Identity** (`homelab-automation`, Universal Auth) set up for programmatic access. Credentials in `scripts/.infisical_credentials` (gitignored).
- ✅ `scripts/infisical_client.py` — thin API client (get/set/list/delete), used both as a library and a CLI. Project: "Homelab Secrets" (`12b81f55-e5b6-4296-93ea-b96879f6ef65`), environment `prod`.
- ✅ **13 secrets migrated** (`scripts/migrate_secrets_to_infisical.py`, re-runnable) — everything that was readable from a `.env` file on disk: Sonarr/Sonarr-4K/Radarr/Radarr-4K/Prowlarr/Overseerr/Tautulli API keys, qBittorrent username+password, Vikunja's JWT secret and its second-brain API token, brain-bot's Discord bot token, and n8n's own public API key.
- ⬜ **Not migrated — only ever existed in n8n's own encrypted credential store**, which never exposes stored values for reading via its API: Mac Mini SSH password, Notion token, Entra Graph app credentials, the "Homelab Discord Webhook"/"Earned It Discord Webhook" webhook URLs. These would need to be re-entered by hand into Infisical if you want them centralized too — I can't extract them from n8n programmatically, confirmed constraint from earlier work.
- ✅ Postgres backups running (workflow 03, daily, `pg_dump | gzip`, keep-last-7, verified with a real live dump). See `docs/containers/infisical.md`.
- ⚠️ **Still open**: the `ENCRYPTION_KEY` itself (in `infisical/.env`) has no backup anywhere outside this one file. The Postgres dump alone can't be restored without it — losing this specific value with no separate copy means the 13 secrets already migrated become unrecoverable even though the dump file itself is fine. This needs a copy stored somewhere outside this repo (a different password manager, a physical note) — deliberately not bundled into the same automated backup as the data it protects.
- ⚠️ **qBittorrent's WebUI password is still a weak default value, and it's been visible in this public repo's history** — found this migrating it over. This is a real, active exposure (not hypothetical) and independent of anything else in this doc; rotate it directly in qBittorrent's own WebUI settings as soon as possible, then update the value here and in `homepage/.env`.

## What "secret rotation" honestly means here

Infisical's own marketing leans on "automatic secret rotation" as a feature, but two things are worth being direct about:

1. **Self-hosted Community Edition is feature-gated.** Confirmed directly from this instance's own startup log: `"Current license does not support custom rate limit configuration"`. That's not about rotation specifically, but it proves the free self-hosted tier isn't the full product — whether Infisical's polished rotation UI is available on this tier needs to be verified once there's a project to test it in, not assumed from their marketing page.
2. **Even where Infisical's own rotation feature *is* available, rotation for a given credential is only as good as whatever regenerates that credential at the source.** Infisical can store a new value and mark the old one revoked, but *something* has to actually produce a new, valid credential from the service that issued it in the first place. For a lot of what's in this homelab, that "something" is a human clicking a button — not an API.

So rather than promise blanket automated rotation, here's an honest breakdown of what's actually rotatable via API vs. not, for every credential currently in use:

| Credential | Rotatable via API? | Notes |
|---|---|---|
| Vikunja API token | **No, corrected 2026-08-26** | Originally claimed yes here without testing it — wrong. Tested directly: `GET /api/v1/tokens` (and by extension create/delete) rejects the personal access token itself with a 401, `"missing, malformed, expired or otherwise invalid token provided"`. Token management requires an actual logged-in user session (JWT from `/api/v1/login`), not the API token — meaning real automated rotation would mean storing Kody's actual Vikunja login password in Infisical just to mint a JWT for this one purpose, which is a materially bigger thing to automate than "rotate an API key." Not doing that without it being a deliberate, separate decision. |
| Trilium ETAPI token | **Probably** | Trilium's ETAPI has token management endpoints — needs to be verified against the exact running version before relying on it, not assumed. |
| Sonarr / Radarr / Radarr-4K / Sonarr-4K (Servarr family) | **Likely yes, partially verified** | `GET /api/v3/config/host` returns an `apiKey` field as part of the normal host-config resource — checked directly against the real Sonarr instance. That resource is `PUT`-able in the Servarr API, so setting a new key is probably just a `PUT` with a new `apiKey` value. **Not yet exercised end-to-end** — actually flipping it would immediately break every other integration still using the old key (n8n workflows, Homepage's widget, Unpackerr) until each is updated too, so this needs a coordinated rotation (mint new key, update every consumer, confirm all working, only then treat the old key as gone) rather than a quick test. |
| Prowlarr / Tautulli API keys | **Unverified** | Same family of apps, plausibly the same pattern as above (Prowlarr shares Servarr's API design), but not checked yet. Don't assume yes without testing this specific instance. |
| Overseerr API key | **Unverified** | Same caveat as above. |
| Mac Mini SSH password | **Technically yes, deliberately not automated** | Scriptable via `dscl`/`passwd` over the same SSH connection, but this is the login the entire homelab management flow depends on — high blast radius if a rotation script gets it wrong mid-run. Keep this one human-initiated. |
| Discord bot token (brain-bot + second-brain-bot) | **No** | Only regeneratable from the Discord Developer Portal by a human — this is a deliberate Discord security design, not a gap here. |
| Notion API token | **No** | Same — only regeneratable from Notion's own integration settings page. |
| Entra Graph app credentials | **No** (not even connected to a real tenant yet) | Would go through Entra's own admin portal when it exists. |
| Strava OAuth | **No** (not connected yet) | OAuth token refresh is automatic once connected (that's what OAuth refresh tokens are for), but *revoking and re-authorizing* the app connection itself is a human action in Strava's settings. |
| Homelab / Earned It Discord webhooks | **Yes, sort of** | Deleting and recreating a Discord webhook is a simple API call, but there's rarely a real reason to rotate a webhook URL unless it's been leaked. |
| n8n's own encryption key, Infisical's own `ENCRYPTION_KEY`/`AUTH_SECRET`/DB password | **No** | These are root-of-trust secrets for the systems that manage *other* secrets — rotating them is a deliberate, disruptive, manual operation (re-encrypting everything downstream), not something to script casually. |

## The realistic plan

1. ✅ Admin account + machine identity created.
2. ✅ Genuinely-static, low-risk credentials migrated into Infisical as a storage exercise — real value (one inventory instead of five `.env` files) even with zero rotation built yet.
3. **Correction, 2026-08-26**: originally planned to build Vikunja token rotation first as the "clearly-supported case" — tested it directly and it isn't one (see table above). Redirected to the Servarr family (Sonarr/Radarr) instead, which looks genuinely promising (`apiKey` is a normal field on a `PUT`-able config resource) but needs a coordinated rotation — mint new key, update n8n + Homepage + Unpackerr, confirm all still work, retire the old key — not a quick one-off test, since flipping it live would break those integrations until each is updated.
4. For everything still marked "unverified" above, test the specific app's actual API before claiming it's rotatable — no claiming a capability exists without exercising it against this homelab's real running version. (Lesson from step 3: don't repeat the Vikunja mistake.)
5. Discord/Notion/Entra/Strava/SSH stay human-initiated by design — rotation there means "make it easy for you to update the stored value after you regenerate it at the source," not "fully automated," and that's a reasonable, honest scope for this project.
