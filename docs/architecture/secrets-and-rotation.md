# Secrets Store & Rotation

Infisical (`docs/containers/infisical.md`) is now running as the intended central home for this homelab's credentials. This doc covers two separate things people often conflate: **storing** secrets centrally (straightforward, Infisical does this well) and **rotating** them (harder, and honestly assessed per-service below rather than assumed).

## Status as of 2026-08-26

- ✅ Infisical stack running (`infisical/`), Postgres + Redis + app, LAN-only at `192.168.178.69:30034`.
- ⏳ **Blocked on you**: the admin account has to be created by hand at `http://192.168.178.69:30034/admin/signup` — same reasoning as Vikunja/Trilium, this is the root of trust for every secret that'll ever live here, not something the second brain should self-serve.
- ⏳ **Blocked on you (after that)**: create an **Infisical Machine Identity** (Org Settings → Machine Identities → Create) with at least read/write access to a project, and give me its **Client ID and Client Secret**. That's what lets scripts/n8n talk to Infisical programmatically instead of using your own login. This is the same pattern as the Vikunja token — you generate it, I wire it in.
- ⬜ Not started: actually migrating the ~20 existing credentials (currently split across 5 `.env` files and n8n's credential store) into Infisical. Straightforward once the machine identity exists — this doc has the plan below, not yet executed.
- ⬜ Not started: backing up `infisical/data/postgres` and the `ENCRYPTION_KEY` from `infisical/.env`. Until this exists, Infisical is a *worse* place to keep something than a backed-up `.env` file would be — losing that key with no backup makes everything stored genuinely unrecoverable. This should happen before any real secret gets migrated in, not after.

## What "secret rotation" honestly means here

Infisical's own marketing leans on "automatic secret rotation" as a feature, but two things are worth being direct about:

1. **Self-hosted Community Edition is feature-gated.** Confirmed directly from this instance's own startup log: `"Current license does not support custom rate limit configuration"`. That's not about rotation specifically, but it proves the free self-hosted tier isn't the full product — whether Infisical's polished rotation UI is available on this tier needs to be verified once there's a project to test it in, not assumed from their marketing page.
2. **Even where Infisical's own rotation feature *is* available, rotation for a given credential is only as good as whatever regenerates that credential at the source.** Infisical can store a new value and mark the old one revoked, but *something* has to actually produce a new, valid credential from the service that issued it in the first place. For a lot of what's in this homelab, that "something" is a human clicking a button — not an API.

So rather than promise blanket automated rotation, here's an honest breakdown of what's actually rotatable via API vs. not, for every credential currently in use:

| Credential | Rotatable via API? | Notes |
|---|---|---|
| Vikunja API token | **Yes** | Vikunja's own REST API supports creating and revoking personal access tokens (`POST`/`DELETE /api/v1/tokens`) — a script can mint a new one and revoke the old, no human needed. Best candidate for real automated rotation. |
| Trilium ETAPI token | **Probably** | Trilium's ETAPI has token management endpoints — needs to be verified against the exact running version before relying on it, not assumed. |
| Sonarr / Radarr / Radarr-4K / Sonarr-4K / Prowlarr / Tautulli API keys | **Unverified, likely partial** | These apps generally regenerate their API key via their own Settings UI; whether each exposes a documented API endpoint to do the same without touching the config file directly needs per-app verification before claiming it works. Don't assume yes. |
| Overseerr API key | **Unverified** | Same caveat as above. |
| Mac Mini SSH password | **Technically yes, deliberately not automated** | Scriptable via `dscl`/`passwd` over the same SSH connection, but this is the login the entire homelab management flow depends on — high blast radius if a rotation script gets it wrong mid-run. Keep this one human-initiated. |
| Discord bot token (brain-bot + second-brain-bot) | **No** | Only regeneratable from the Discord Developer Portal by a human — this is a deliberate Discord security design, not a gap here. |
| Notion API token | **No** | Same — only regeneratable from Notion's own integration settings page. |
| Entra Graph app credentials | **No** (not even connected to a real tenant yet) | Would go through Entra's own admin portal when it exists. |
| Strava OAuth | **No** (not connected yet) | OAuth token refresh is automatic once connected (that's what OAuth refresh tokens are for), but *revoking and re-authorizing* the app connection itself is a human action in Strava's settings. |
| Homelab / Earned It Discord webhooks | **Yes, sort of** | Deleting and recreating a Discord webhook is a simple API call, but there's rarely a real reason to rotate a webhook URL unless it's been leaked. |
| n8n's own encryption key, Infisical's own `ENCRYPTION_KEY`/`AUTH_SECRET`/DB password | **No** | These are root-of-trust secrets for the systems that manage *other* secrets — rotating them is a deliberate, disruptive, manual operation (re-encrypting everything downstream), not something to script casually. |

## The realistic plan

1. You create the Infisical admin account and a machine identity (above).
2. I migrate the genuinely-static, low-risk credentials into Infisical first (API keys for the media stack, webhooks) as a storage exercise — this alone is real value (one inventory instead of five `.env` files + n8n's store) even before any rotation exists.
3. I build a rotation script specifically for Vikunja's token (the one clearly-supported case) as a working example of what automated rotation actually looks like here, store both old/new values' history in Infisical, and verify it end-to-end against the real Vikunja instance rather than assuming the API contract.
4. For everything marked "unverified" above, I test the specific app's actual API before claiming it's rotatable — no claiming a capability exists without having exercised it against this homelab's real running version.
5. Discord/Notion/Entra/Strava/SSH stay human-initiated by design — rotation there means "make it easy for you to update the stored value after you regenerate it at the source," not "fully automated," and that's a reasonable, honest scope for this project.
