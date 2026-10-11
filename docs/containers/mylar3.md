# Mylar3

Comics automation, the Sonarr of the stack for comics. You add a series; it tracks new issues on ComicVine, searches Prowlarr's indexers, sends grabs to qBittorrent, and files finished issues into the comics library on the NAS, where Komga picks them up.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/mylar3:latest` (Mylar `v0.11.0` stable at deploy; linuxserver now builds the maintained MylarComics fork) |
| **Container name** | `mylar3` |
| **Compose file** | `mylar3/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30046:8090`: host `30046` → container `8090` |
| **Local URL** | `http://192.168.178.69:30046` |
| **Public URL** | none yet. `mylar.kodyparton.com` is **deliberately held back until Mylar has a login**: it ships with none, and every NPM host is reachable from the internet through the WAN port-forward (see `architecture/known-issues.md`) |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `Europe/Amsterdam` |
| **Restart policy** | `unless-stopped` |
| **Network** | `network_mode: bridge`, because Docker's address pools are nearly exhausted (see `known-issues.md`). It reaches Prowlarr and qBittorrent by the host IP, like the other *arrs |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `mylar3/config` | `/config` | `config/mylar/config.ini` (holds the ComicVine key, qBittorrent password, API key), `mylar.db` (the watchlist), logs | gitignored (`*/config/`); `config.ini` is mode 600 |
| `nas_comics_v3` (CIFS, `//192.168.178.38/media/comics`) | `/comics` | the library, **read-write** | Komga mounts the same volume **read-only**, so Mylar is the only thing that writes to the library |
| `nas_downloads` (CIFS, `//192.168.178.38/downloads`) | `/mnt/downloads` | qBittorrent's downloads; Mylar watches `/mnt/downloads/comics` | **same container path as qBittorrent and every *arr**, so download paths match without a remote path mapping |

## How it's wired

1. **Add a series** in Mylar. It pulls the issue list from ComicVine.
2. **Search**: Torznab providers pushed in by **Prowlarr** (app id 6, `Mylar3`, full sync, category `7030` Books/Comics). **IPTorrents is the search provider**: `IPTorrents (Prowlarr)`, enabled, category `7030`. It was verified 2026-10-11 to return comics (100 results each for "Batman" and "Spider-Man", including 2026 releases). Some results are ebook/PDF-style releases (`… HYBRID COMIC eBook`, `Retail eBook`), not just CBR/CBZ. `Ebooks-Shares (Prowlarr)` is also listed but **disabled** (no definition in Prowlarr). ABtorrents has no comics category, so it isn't synced.
3. **Grab** → qBittorrent (`torrent_downloader = 5`), category **`comics`** → `/mnt/downloads/comics`. The category was created 2026-10-11 and uses qBittorrent's global share limits, like every other category.
4. **Import**: the folder monitor (`enable_check_folder`, `check_folder = /mnt/downloads/comics`, every 5 min) renames finished downloads (`$Series ($Year)/$Series $Annual $Issue ($Year)`) and **copies** them into `/comics` (`file_opts = copy`). Copy, not move: qBittorrent keeps seeding until its global limits (ratio 2, or 25,160 min) and then removes the torrent and its files itself. In Mylar's post-processor, `copy` means `shutil.copy` and the source is left alone.
5. **Komga** shows new issues after its next library scan, or straight away with "Scan library files".

`scripts/configure_mylar3.py` writes all of this into `config.ini`. Run it with the container stopped (Mylar can write its in-memory config back over a live edit). It only touches its own keys and keeps everything else, including Prowlarr's synced providers.

## Dependencies

- **Depends on:** ComicVine API (metadata), Prowlarr (indexers), qBittorrent (downloads), the UNAS Pro (both CIFS volumes).
- **Depended on by:** Komga (reads what Mylar files), Homepage (Mylar3 card with a live widget).

## Credentials & Secrets

All in Infisical, written into `config.ini` by `configure_mylar3.py`, never printed:
- `COMICVINE_API_KEY`: from Kody's free ComicVine account. Verified: a search for "Secret Wars" returned 66 series.
- `MYLAR_API_KEY`: generated 2026-10-11. Used by Prowlarr's app sync and by Homepage (`HOMEPAGE_VAR_MYLAR_API_KEY`).
- `QBITTORRENT_USERNAME` / `QBITTORRENT_PASSWORD`: Infisical's password was **stale** and was corrected the same day (see `qbittorrent.md`). Mylar has the corrected one.
- **Web login: not set yet. Kody sets it** under Settings → Web Interface → Authentication. Prefer **Form** login: with Basic auth, Prowlarr's Mylar app would also need `authUsername`/`authPassword` filled in, or its sync breaks.

## External Access

None yet. After the login exists: AdGuard rewrite + NPM proxy host `mylar.kodyparton.com` → `http://192.168.178.69:30046` (HTTP/2 + HSTS on, like the rest), a Kuma entry, and the Homepage `href` moved from the IP to the hostname.

## Backups

None yet. `config/mylar/mylar.db` holds the watchlist and history, and is worth adding to workflow 03 once series are being tracked.

## Automation

- **02 - Docker Drift Detection**: automatic (walks every `*/compose.yml`).
- **Watchtower**: watches all containers.
- **Prowlarr app sync** keeps Mylar's indexer list current (full sync; Prowlarr's other apps were repointed the same day, so all of them sync again).

## Known Issues / Gotchas

- **Coverage depends on the indexers.** One comic-capable indexer works (IPTorrents), and it has deep comics coverage. Ebooks-Shares is disabled in Prowlarr.
- **`get_imprint_volume_and_booktype ... 'NoneType' object has no attribute 'items'`** errors during ComicVine searches come from Mylar parsing results with no imprint data. They're harmless: the search still returns its results.
- **No family requests.** Mylar is single-login with no request flow, so series are added by Kody. A possible later addition: a Discord "request a comic" command (Brain Bot → n8n → Mylar's API).
- **The existing library isn't tracked by Mylar.** Manage → Import can match the Secret Wars collection to ComicVine series if Mylar should fill gaps or watch them. Optional.
- **11th container on a native CIFS volume** (two of them here): same creation-time failure mode as the rest. `scripts/cifs_volume_health_check.sh` covers it by container state.

## Change Log

- `2026-10-11`: Deployed at Kody's request ("requesting comics like Sonarr/Radarr"); chosen over Kapowarr because it plugs into the existing Prowlarr → qBittorrent → library flow. qBittorrent category `comics` created; config written from Infisical (ComicVine key verified live, 66 results); Prowlarr app `Mylar3` (id 6) added, connection test passed, 2 providers synced; Homepage card with live widget (API key accepted; "no data" until a series is added). Hostname held until Kody sets the web login. While wiring qBittorrent, found and fixed qBittorrent being **open to the internet with no password** (see `qbittorrent.md`).
