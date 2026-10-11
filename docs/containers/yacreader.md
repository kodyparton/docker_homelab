# YACReader

Headless YACReaderLibrary Server: serves the comics library on the NAS to the YACReader iOS/Android apps and to a basic browser UI. The comics counterpart of Audiobookshelf and LazyLibrarian.

## Quick Facts

| | |
|---|---|
| **Image** | `xthursdayx/yacreaderlibrary-server-docker:unarr` (YACReaderLibraryServer `v1.8.2`, linuxserver.io base) |
| **Container name** | `yacreader` |
| **Compose file** | `yacreader/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30044:8080`: host `30044` → container `8080` |
| **Local URL** | `http://192.168.178.69:30044` (browser UI at `/webui`) |
| **Public URL** | `https://comics.kodyparton.com` (LAN-only DNS, via NPM proxy host 25) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `Europe/Amsterdam` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `nas_comics_v3` (Docker CIFS volume, `//192.168.178.38/media/comics`) | `/comics` | comics library **and its index** (`.yacreaderlibrary/`) | native CIFS, `vers=3.0,nobrl,uid=1000,gid=1000`, created by hand (`external: true`). **`nobrl` is required**, see Known Issues. The original `nas_comics` volume (no `vers`, no `nobrl`) is unused but not removed |
| `yacreader/config` | `/config` | server settings | gitignored (`*/config/`) |

YACReader keeps each library's database in a hidden `.yacreaderlibrary/` folder **inside the library root**, not in `/config`. Once a library is created, its index lives on the NAS next to the comics, so `/config` holds only the server settings file (`/config/.local/share/YACReader/YACReaderLibrary/YACReaderLibrary.ini`) and the list of libraries.

## Dependencies

- **Depends on:** the UNAS Pro (`nas_comics` volume).
- **Depended on by:** Homepage (container-status card under the media group, `homepage/config/services.yaml`).

## Credentials & Secrets

None. YACReaderLibraryServer has **no authentication**: anyone who can reach port `30044` (or `comics.kodyparton.com`) can browse and download the whole library. That is acceptable on the LAN. It is why this must never get a public DNS record or a port forward without an NPM access list or Authelia in front.

## External Access

- **AdGuard Home rewrite** `comics.kodyparton.com` → `192.168.178.69`: added 2026-10-11 through the AdGuard API (`do_dns_api()` from `scripts/add_device_proxy_hosts.py`, credential from Infisical). Verified with `dig +short comics.kodyparton.com @192.168.178.69` → `192.168.178.69`.
- **NPM proxy host 25**: `comics.kodyparton.com` → `http://192.168.178.69:30044`, wildcard cert id 1, SSL forced, websockets on. Created by Kody in the UI on 2026-10-11. Its advanced config replaces NPM's default `location /` so it can send `Host: $host:$server_port`; see Known Issues for why. **Don't clear that advanced config**, or the server will start crashing again.
- Not in public (Cloudflare) DNS.

## Backups

None, and not in workflow 03. Low stakes: the comics are on the NAS, and the library index can be rebuilt with a rescan. Nothing unique lives in `/config`.

## Automation

- **02 - Docker Drift Detection**: picked up automatically, because `scripts/drift_check.sh` walks every `*/compose.yml`.
- **Watchtower**: watches all containers, so this one too. In practice, see the image note below.
- **Uptime Kuma**: `comics.kodyparton.com` is listed in `scripts/kuma_seed_monitors.js` but **not seeded yet**. `KUMA_ADMIN_PASSWORD` isn't in Infisical, so the script has to be run interactively (`bash scripts/kuma_seed_monitors.sh`).
- **Library rescan**: manual. YACReader doesn't watch the folder, so after adding comics run `docker exec yacreader YACReaderLibraryServer update-library /comics`.

## Known Issues / Gotchas

- **A `Host` header with no port crashes the server.** YACReaderLibraryServer 1.8.2 dies on any request whose `Host` is a bare hostname (`comics.kodyparton.com`), and s6 restarts it a second later. `192.168.178.69`, `192.168.178.69:30044` and `comics.kodyparton.com:443` are all fine, which is why direct access always looked healthy. NPM sends `Host: $host` by default, so every proxied request killed the server, and the next request hit it mid-restart and got a 502. Fixed with a custom `location /` in proxy host 25's advanced config that sends `Host: $host:$server_port`. Diagnosed by sending different `Host` headers straight at port 30044 and checking whether the server was still alive afterwards.
- **Proxy host 25 must keep HTTP/2 on.** It was created with HTTP/2 and HSTS off, unlike every other `*.kodyparton.com` host. Safari reuses one HTTP/2 connection across hosts that share the wildcard cert, so going from any other homelab page to comics gave **421 Misdirected Request**. curl, opening a fresh connection, got 200, which hid the problem. Turned on (`http2_support`, `hsts_enabled`, `hsts_subdomains`) to match `audiobooks` on 2026-10-11.
- **The library index needs `nobrl` on its CIFS mount.** YACReader keeps its SQLite DB (`library.ydb`) inside the library folder on the NAS. On the original `nas_comics` volume (no `nobrl`, no `vers=3.0`), `create-library` reported `36 comics processed` and wrote 36 covers, but `library.ydb` stayed **0 bytes**. SQLite's byte-range locks fail over SMB without telling you. Fixed by creating `nas_comics_v3` with the same options plus `vers=3.0,nobrl` (`vers=3.0` matches every other `nas_*` volume) and rescanning. The DB came out at 106 KB. The failed index was renamed to `/comics/.yacreaderlibrary.broken-20261011`, not deleted, and can be removed.
- **Library created 2026-10-11**: `Comics` → `/comics`, 36 comics (one folder, `Secret Wars Collection (2015)`).
- **No `.cb7`/7z support.** The scan logs `7z support requires 7z SDK`; this image build can't read 7z archives. `.cbz`/`.cbr` are fine. None of the current files are 7z.
- **The image is stale.** The `unarr` tag (the variant built with unarr, so it can read `.cbr`/RAR) was last built 2024-02-06. Watchtower will never find an update for it. If YACReader upstream ships a fix you need, this tag will not get it.
- **`nas_comics_v3` makes this the 10th container on a native CIFS volume.** If the NAS is unreachable when the container is created (Watchtower recreate, `compose up`, OrbStack restart), it fails at creation and stays down, the same way the other nine did on 2026-09-17. `scripts/cifs_volume_health_check.sh` finds affected containers by state, not by a hard-coded list, so it covers this one with no change.
- **The volume options hold the NAS password in plaintext**, the same as every other `nas_*` volume (visible in `docker volume inspect nas_comics_v3`). They are not in the repo, because the volume is `external`. Don't paste `docker volume inspect` output anywhere public.

## Change Log

- `2026-10-11`: Container deployed (`yacreader/compose.yml`, port `30044`, `nas_comics` CIFS volume). Homepage card added, AdGuard rewrite for `comics.kodyparton.com` added, doc created. Same day: library created; NPM proxy host 25 (made by Kody) fixed for the Host-header crash; library volume moved to `nas_comics_v3` (`vers=3.0,nobrl`) after the index DB came out empty. Verified `https://comics.kodyparton.com/webui` → 200 (valid cert) three times in a row with no server restarts, and `/v2/libraries` lists `Comics`. Later that day Safari got 421 (HTTP/2 off on host 25, see Known Issues); fixed by turning on HTTP/2 and HSTS.
