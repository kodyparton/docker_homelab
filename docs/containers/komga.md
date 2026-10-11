# Komga

Comics server with a full web reader, reading lists and OPDS feeds. Serves the comics library on the NAS for reading on the iPad, in Safari or in an OPDS app like Panels. Replaced YACReader on 2026-10-11, whose browser UI was too bare to read in.

## Quick Facts

| | |
|---|---|
| **Image** | `gotson/komga:latest` (Komga `1.28.1` at deploy, Java 23) |
| **Container name** | `komga` |
| **Compose file** | `komga/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30045:25600`: host `30045` → container `25600` |
| **Local URL** | `http://192.168.178.69:30045` |
| **Public URL** | `https://comics.kodyparton.com`: **public**, through a Cloudflare-proxied record (from home, via the AdGuard rewrite straight to NPM proxy host 25) |
| **PUID/PGID** | runs as `1000:1000` through compose `user:` (not a linuxserver image, so no PUID/PGID) |
| **Timezone** | `Europe/Amsterdam` |
| **Restart policy** | `unless-stopped` |
| **Network** | `network_mode: bridge` (Docker's built-in bridge), **not** its own compose network. See Known Issues |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `komga/config` | `/config` | SQLite database (users, read progress, metadata), search index, thumbnails, logs; `application.yml` goes here too | gitignored (`*/config/`). **Deliberately on local disk**: SQLite on the SMB share is what broke YACReader's index |
| `nas_comics_v3` (Docker CIFS volume, `//192.168.178.38/media/comics`) | `/data/comics` | comics library | **read-only** (`:ro`), because Komga never needs to write to the library. Native CIFS, `vers=3.0,nobrl,uid=1000,gid=1000` (originally created for YACReader, now Komga's alone) |

## Dependencies

- **Depends on:** the UNAS Pro (`nas_comics_v3` volume). New issues arrive from **Mylar3**, which writes into the same volume read-write; Komga picks them up on its next library scan.
- **Depended on by:** Homepage (Komga card in the Personal group; its widget is staged, see `homepage.md`).

## Credentials & Secrets

- **Admin account:** claimed by Kody on 2026-10-11, with his Gmail address as the email. That's what lets Google sign-in link to it. The password isn't in Infisical (`KOMGA_ADMIN_PASSWORD` would be the name, if stored). It wasn't created by automation on purpose: account creation and choosing its password are the owner's to do.
- **Google OAuth client:** `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` in Infisical (Kody created the client on 2026-10-11, in Testing mode, with test users as the allowlist), written into the gitignored `komga/.env` (mode 600) by `scripts/env_from_infisical.py`. It's one client shared by every app in the Google sign-in rollout.
- Family members get their own Komga users (Server Settings → Users), with their Gmail addresses as the email, so Google sign-in can match them later.
- Homepage widget (staged): `HOMEPAGE_VAR_KOMGA_USERNAME` / `HOMEPAGE_VAR_KOMGA_PASSWORD`. Any non-admin user works.

## External Access

- **NPM proxy host 25**: `comics.kodyparton.com` → `http://192.168.178.69:30045`, wildcard cert id 1, SSL forced, HTTP/2 + HSTS on, websockets on, **no advanced config**. Repointed from YACReader (`:30044`) on 2026-10-11. YACReader's `Host`-with-port workaround was removed at the same time: Komga doesn't need it, and it would put `:443` into the absolute URLs Komga builds for OPDS feeds and the OAuth2 redirect.
- **AdGuard rewrite** `comics.kodyparton.com` → `192.168.178.69`: the existing one from the YACReader setup, unchanged.
- **Public via Cloudflare (2026-10-11):** Kody added a **proxied** `comics` record, the same pattern as `request`/`n8n`. Cloudflare's edge reaches NPM through the modem's WAN `:443` port-forward (verified 200 through the edge). Because the record is public, the name now resolves on every device, including ones not using AdGuard and Safari with iCloud Private Relay. At home, devices that do use AdGuard still go straight to NPM. Exposure: Komga's own login is the only gate, with no lockout after repeated wrong passwords. See `architecture/known-issues.md` for the wider port-forward exposure and the Cloudflare Tunnel recommendation.

### Reading on the iPad

- **Browser (free):** open the URL in Safari → Share → **Add to Home Screen** for a full-screen reader. Supports paged, double-page spreads (good on a 12.9" screen), webtoon scroll, and swipe navigation.
- **Panels (OPDS):** Library → Connect Service → OPDS. Server `https://comics.kodyparton.com/opds/v1.2/catalog` (or `http://192.168.178.69:30045/opds/v1.2/catalog`), with your Komga email + password. Supports streaming, offline downloads and read-progress sync. **Panels needs Panels+ or its one-time purchase for OPDS.** Official guide: https://komga.org/docs/guides/panels

## Backups

None yet, and not in workflow 03. The comics are on the NAS. The only unique data is `config/database.sqlite`: users, read progress, reading lists and edited metadata. Worth adding to `scripts/backup_check.sh` once there's real read progress to lose.

## Automation

- **02 - Docker Drift Detection**: picked up automatically (`scripts/drift_check.sh` walks every `*/compose.yml`).
- **Watchtower**: watches all containers, so `latest` stays current.
- **Uptime Kuma**: `comics.kodyparton.com` is in `scripts/kuma_seed_monitors.js` as **Komga**, not seeded yet (needs `KUMA_ADMIN_PASSWORD`, which isn't in Infisical).
- **Library scans**: Komga rescans on its per-library schedule, and on demand from the library menu (**Scan library files**). Don't rely on its filesystem watcher: changes made on the NAS by other clients don't raise inotify events through a CIFS mount.

## Known Issues / Gotchas

- **`network_mode: bridge` because Docker ran out of subnets.** `docker compose up` failed with `all predefined address pools have been fully subnetted`. The stack has 30 networks, one per compose project, and Docker's default pools allow about 31. None were unused. Komga talks to no other container, so it joined the built-in `bridge` instead. **The next new compose project will hit the same wall**, see `architecture/known-issues.md`.
- **File formats verified at deploy:** all 36 files read fine. 26 are `.cbr`, all **RAR4 and non-solid** (main-header flag `0x0008` checked on every file), and 10 are `.cbz`. Komga reads CBZ/CBR, PDF and EPUB, and RAR5 on Docker arm64 through a native library, but **not solid RAR archives**. If a future `.cbr` won't open, check it isn't solid (`unrar lt` shows it) and repack it as `.cbz`.
- **Library layout → series:** Komga makes a series from each folder that contains books. `Secret Wars Collection (2015)/` holds one folder per title (e.g. `1872 (001-004) (2015)`), so each title becomes its own series. Add the library at root folder `/data/comics`.
- **Google sign-in: ENABLED 2026-10-11** (see `architecture/sso.md`):
  - **Wiring:** `compose.yml` loads an **optional** `env_file: .env` holding `SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_CLIENTID` / `_CLIENTSECRET` (template in `.env.example`). It's optional because an empty client ID stops Spring at startup; with no `.env`, Komga runs with password login only. `KOMGA_OAUTH2ACCOUNTCREATION=false` is set explicitly, so a Google login only links to a Komga user that **already exists with the same email** (Komga's default, stated so it can't silently change). `KOMGA_OIDCEMAILVERIFICATION` keeps its default `true`, and Gmail addresses are always verified.
  - **Enable**, once the client is in Infisical:
    `python3 scripts/env_from_infisical.py komga SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_CLIENTID=GOOGLE_OAUTH_CLIENT_ID SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_CLIENTSECRET=GOOGLE_OAUTH_CLIENT_SECRET`
    then `docker compose up -d` in `komga/`. Run on 2026-10-11.
  - **Verified after enabling:** `/api/v1/oauth2/providers` → Google. The authorization redirect carries the real client ID and the https redirect URI. **Google accepted the real request** (→ its sign-in page) and **rejected the same request with a bogus redirect URI** (`redirect_uri_mismatch`), which proves the registered URI is exact and that Google is really checking it. The container reaches `oauth2.googleapis.com` for the code exchange.
  - **Proxy headers need no change:** Komga's bundled `application.yml` already sets `server.forward-headers-strategy: framework` (read from the jar), so it trusts NPM's `X-Forwarded-Proto`.
  - **Dry run, 2026-10-11, with a fake client ID:** `/api/v1/oauth2/providers` → `[{"name":"Google","registrationId":"google"}]`. `/oauth2/authorization/google` redirected to `accounts.google.com` with `redirect_uri=https://comics.kodyparton.com/login/oauth2/code/google` and `scope=openid profile email`, both via NPM on the LAN **and** through Cloudflare's edge. The fake client was then removed (providers back to `[]`).
  - **Use the hostname for Google sign-in, not `http://192.168.178.69:30045`:** the redirect URI is built from the request's host, and Google only accepts the registered https one.
  - **Panels/OPDS doesn't use Google:** OPDS apps sign in with the Komga **password**. A family member who should use Panels needs a password set on their Komga user as well as the Google link.
- **Heap capped at 1 GB** (`JAVA_TOOL_OPTIONS=-Xmx1g`). Uncapped, the JVM sizes its heap from the whole 12 GB OrbStack VM, which Ollama also uses. Measured 563 MiB just after first start.
- The startup `WARN ... MMapDirectory ... update Apache Lucene` is harmless (Komga's bundled Lucene on Java 23).
- **`ConvertBook ... execution failed: Read-only file system` (×26 in the log):** the `Comics` library was created with **Convert to CBZ** and **Repair extensions** on (`LIBRARY.CONVERT_TO_CBZ=1`, `REPAIR_EXTENSIONS=1`). Komga tries to rewrite each `.cbr` as a `.cbz` next to it (and remove the original), which the read-only mount blocks, so nothing on the NAS changed. It's harmless but repeats on every scan. **Kody's call:** turn both options off (Library → Edit → Options) and keep the library read-only (recommended: CBR reads fine in Komga and Panels, and all 26 are non-solid RAR4), *or* switch the mount to read-write so the conversion actually runs.
- **10th container on a native CIFS volume:** same creation-time failure mode as the others if the NAS is down when it's (re)created. `scripts/cifs_volume_health_check.sh` covers it by container state, with no change needed.

## Change Log

- `2026-10-11`: Deployed to replace YACReader for iPad reading. `komga/compose.yml` (port `30045`, `nas_comics_v3` mounted read-only, 1 GB heap, `network_mode: bridge` after Docker's subnet pools ran out). NPM proxy host 25 (`comics.kodyparton.com`) repointed here, with YACReader's advanced config removed. Homepage card swapped from YACReader to Komga (widget staged), and the Kuma entry renamed. Verified `https://comics.kodyparton.com/` → 200 over HTTP/2 with a valid cert, and http→https redirect. **Pending (Kody): claim the admin account and add the `/data/comics` library.**
- `2026-10-11` (night): YACReader removed. Komga is now the only comics service and the sole user of `nas_comics_v3`.
- `2026-10-11` (late): Kody claimed the admin account (his Gmail address) and added the `Comics` library (`/data/comics`). Kody added a proxied Cloudflare record for `comics`, which is now public (200 through Cloudflare's edge). Google sign-in staged: optional `env_file`, `KOMGA_OAUTH2ACCOUNTCREATION=false`, `.env.example`, and a new `scripts/env_from_infisical.py`. Dry-run verified with a fake client (correct https redirect URI through NPM and through Cloudflare), then reverted. Waiting on the real Google OAuth client.
- `2026-10-11` (evening): **Google sign-in enabled.** Kody stored the Google OAuth client in Infisical; `komga/.env` written by `env_from_infisical.py`, Komga recreated. Google accepted the real authorization request and rejected a bogus redirect URI. Waiting on Kody's first real login. Found the library's Convert-to-CBZ option failing against the read-only mount (see Known Issues).
- `2026-10-11` (night): **First real Google login confirmed.** Komga's `AUTHENTICATION_ACTIVITY` table shows `OAuth2:Google`, success, at 18:38 UTC, linked to Kody's admin account by email. That table is the place to check sign-ins (`SOURCE` is `Password` or `OAuth2:Google`).
