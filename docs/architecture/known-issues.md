# Known Issues

Running log of infra problems found, their root cause, and whether they're fixed. Update this whenever something new turns up or something on this list gets resolved.

## Open

### `downloads.kodyparton.com` routes to a dead host
- **Found:** 2026-08-17 (rediscovered 2026-08-24, still open)
- **What:** NPM's proxy host for qBittorrent forwards to `10.10.0.130:30024`, a host that doesn't respond to ping — same class of stale-migration issue as the n8n one below, just never fixed for this domain.
- **Actual location:** `192.168.178.69:30024` (this Mac, `network_mode: host`).
- **Fix (manual, NPM UI):** `192.168.178.69:81` → Hosts → Proxy Hosts → edit `downloads.kodyparton.com` → Forward Hostname/IP `192.168.178.69`, Forward Port `30024` → Save.
- **Why manual:** direct writes to NPM's live database/container have been blocked by a safety check as production-infrastructure changes that should go through NPM's own UI/API rather than a raw file/DB edit — see the NPM doc for why a DB row alone isn't even sufficient (routing is driven by generated nginx conf files, not just the database).

### `home.kodyparton.com` (Homepage internal URL) not yet live
- **Found:** 2026-08-24 (in progress)
- **What:** Two manual steps outstanding — a Cloudflare DNS record and an NPM proxy host. See `docs/containers/homepage.md` → External Access for exact values.
- **Why manual:** same reasoning as above; also, this one genuinely needs a real Cloudflare dashboard action from the account owner regardless of tooling.

### SMB mount passthrough — deeper fix deferred
- **Found:** 2026-08-24
- **What:** Root cause of the recurring Sonarr/Radarr/qBittorrent "lost connectivity" complaints — SMB shares mounted on the macOS host, passed through OrbStack's VM into containers, occasionally drop (`ENOENT`). Self-healing (workflow 09, restarts affected containers every 15min) is in place and covers the symptom.
- **Deeper fix (not done):** have containers mount the NAS via native Linux CIFS directly, bypassing the host-passthrough layer entirely — this is the actual fix, not just a workaround, but needs the NAS's SMB username/password (deliberately not extracted from macOS Keychain) and would touch how 5 running services access their data. Deferred at the user's choice on 2026-08-24 in favor of shipping the self-healer first.
- **Also affects (not yet covered by workflow 09):** LazyLibrarian (`/downloads`, `/books`) and Audiobookshelf (`/audiobooks`) use the same SMB shares but aren't in the self-healer's watch list — add them if either ever shows the same symptom.

### Stray duplicate compose file
- **Found:** pre-existing (noticed 2026-08-17)
- **What:** `tautulli/huntarr/compose.yml` is an exact duplicate of `huntarr/compose.yml`, nested in the wrong directory. Not deployed as a second service (only one `huntarr` container runs), but confusing and worth deleting.

### `heimdall/config/compose.yml` was empty — RESOLVED by removal
- No longer relevant — Heimdall was removed entirely 2026-08-17 in favor of Homepage (see below), since it was unconfigured and redundant.

## Resolved

| Date | Issue | Fix |
|---|---|---|
| 2026-08-17 | Live API keys + 4.5GB of runtime data about to be pushed to a **public** GitHub repo | Added `.gitignore`, moved secrets to gitignored `.env` files with committed `.env.example` templates |
| 2026-08-17 | n8n compose referenced undefined `${SUBDOMAIN}`/`${DOMAIN_NAME}`/`${GENERIC_TIMEZONE}`, broke `N8N_HOST` | Added `n8n/.env` |
| 2026-08-17 | n8n's NPM proxy host pointed at a dead host (`10.10.1.5:30065`, pre-migration leftover) | Fixed forward host/port in NPM UI |
| 2026-08-17 | `watchtower` crash-looping — image frozen at a 2023 build, incompatible Docker API version | Switched `containrrr/watchtower` → `nickfedor/watchtower` |
| 2026-08-17 | `lazylibrarian` unreachable — port mapped `30032:30032` but app listens on `5299` | Fixed to `30032:5299` |
| 2026-08-17 | `trilium` never started — bad `/etc/timezone`/`/etc/localtime` host bind mounts (incompatible with OrbStack), wrong data volume path | Removed the bind mounts (added `TZ` env var instead), pointed volume at `./data` |
| 2026-08-17 | `heimdall/config/compose.yml` was empty; service was unconfigured anyway | Removed entirely, replaced by Homepage |
| 2026-08-17 | `audiobookshelf` had never produced a backup — `backupSchedule: false` in settings, never enabled | Enabled daily 3am schedule |
| 2026-08-24 | n8n build agent hardcoded 6 real API keys directly into workflow node parameters instead of using n8n's credential store | Created proper `httpHeaderAuth`/`httpQueryAuth` credentials, rewired all affected nodes, verified zero plaintext keys remain |
| 2026-08-25 | Second brain workflow 18 got reverted to an old pre-redesign version (missing Classify Intent and the whole intent-routing chain) — likely a stale n8n browser tab overwriting newer API-deployed changes on save | Redeployed the correct version. **Lesson**: after editing a workflow via the API, if you also have it open in a browser tab, refresh that tab before saving from it, or the stale copy wins |
| 2026-08-25 | Second brain: any question (not a stored fact, not chat, not a task) silently got zero reply — Ollama's classify step worked correctly, but the "question" branch relied on n8n Switch node's `fallbackOutput` mechanism, which never actually routed the item anywhere, so the item vanished with no error, and n8n's webhook returned an empty 200 | Replaced the fallback-based routing with an explicit `intent === "question"` condition (same proven pattern as the other 4 intents); the true fallback (any unexpected/malformed classify output) now safely routes to the chat branch instead of relying on `fallbackOutput` at all. Also bumped Ollama-calling node timeouts (60s→90-180s) and set `OLLAMA_KEEP_ALIVE=60m` since CPU-only inference in the container is genuinely slow (~35-40s for even a short classify call) — this was the original symptom reported ("failing on Classify Intent"), a real but separate issue from the routing bug |
