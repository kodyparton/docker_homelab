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
| **Public URL** | `https://comics.kodyparton.com` (LAN-only DNS, via NPM proxy host 25) |
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

- **Depends on:** the UNAS Pro (`nas_comics_v3` volume).
- **Depended on by:** Homepage (Komga card in the Personal group; its widget is staged, see `homepage.md`).

## Credentials & Secrets

- **Admin account: not created yet, and that's urgent.** Komga starts unclaimed (`GET /api/v1/claim` → `{"isClaimed":false}`), and **whoever opens it first creates the admin**. Kody creates it on first visit (email + password). Store the password in Infisical as `KOMGA_ADMIN_PASSWORD`. It wasn't created by automation on purpose: account creation and choosing its password are the owner's to do.
- Family members get their own Komga users (Server Settings → Users), with their Gmail addresses as the email, so Google sign-in can match them later.
- Homepage widget (staged): `HOMEPAGE_VAR_KOMGA_USERNAME` / `HOMEPAGE_VAR_KOMGA_PASSWORD`. Any non-admin user works.

## External Access

- **NPM proxy host 25**: `comics.kodyparton.com` → `http://192.168.178.69:30045`, wildcard cert id 1, SSL forced, HTTP/2 + HSTS on, websockets on, **no advanced config**. Repointed from YACReader (`:30044`) on 2026-10-11. YACReader's `Host`-with-port workaround was removed at the same time: Komga doesn't need it, and it would put `:443` into the absolute URLs Komga builds for OPDS feeds and the OAuth2 redirect.
- **AdGuard rewrite** `comics.kodyparton.com` → `192.168.178.69`: the existing one from the YACReader setup, unchanged.
- Not in public (Cloudflare) DNS. **As of 2026-10-11 the name doesn't resolve on Kody's devices** (Tailscale/Ziggo DNS, see `architecture/known-issues.md`), so use `http://192.168.178.69:30045` until that's fixed.

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
- **Google sign-in (planned, see `architecture/sso.md`):** Spring OAuth2 client config goes in `config/application.yml` under `spring.security.oauth2.client.registration.google`. The redirect URI is `https://comics.kodyparton.com/login/oauth2/code/google`. Komga matches Google logins to existing users **by email**; keep `komga.oauth2-account-creation: false` so only pre-created users get in. **Check it builds the redirect URI with `https`** (it's behind NPM, which sends `X-Forwarded-Proto`). If it builds `http`, it isn't trusting forwarded headers and Spring's `server.forward-headers-strategy` needs setting.
- **Heap capped at 1 GB** (`JAVA_TOOL_OPTIONS=-Xmx1g`). Uncapped, the JVM sizes its heap from the whole 12 GB OrbStack VM, which Ollama also uses. Measured 563 MiB just after first start.
- The startup `WARN ... MMapDirectory ... update Apache Lucene` is harmless (Komga's bundled Lucene on Java 23).
- **10th container on a native CIFS volume:** same creation-time failure mode as the others if the NAS is down when it's (re)created. `scripts/cifs_volume_health_check.sh` covers it by container state, with no change needed.

## Change Log

- `2026-10-11`: Deployed to replace YACReader for iPad reading. `komga/compose.yml` (port `30045`, `nas_comics_v3` mounted read-only, 1 GB heap, `network_mode: bridge` after Docker's subnet pools ran out). NPM proxy host 25 (`comics.kodyparton.com`) repointed here, with YACReader's advanced config removed. Homepage card swapped from YACReader to Komga (widget staged), and the Kuma entry renamed. Verified `https://comics.kodyparton.com/` → 200 over HTTP/2 with a valid cert, and http→https redirect. **Pending (Kody): claim the admin account and add the `/data/comics` library.**
- `2026-10-11` (night): YACReader removed. Komga is now the only comics service and the sole user of `nas_comics_v3`.
