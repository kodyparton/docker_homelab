# qBittorrent

Torrent download client — receives grabs from Sonarr/Radarr (all 4 instances) and Prowlarr, downloads to the shared `/mnt/downloads` share where the *arr apps pick finished files up for import.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/qbittorrent:latest` |
| **Container name** | `qbittorrent` |
| **Compose file** | `qbittorrent/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) — **`network_mode: host`**, not bridged |
| **Port(s)** | WebUI `30024` (via `WEBUI_PORT` env, no `ports:` mapping needed under host networking), torrenting `50415` |
| **Local URL** | `http://192.168.178.69:30024` |
| **Public URL** | `https://downloads.kodyparton.com` (via NPM) — **currently misrouted, see Known Issues** |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `qbittorrent/config` | `/config` | app config, session state, GeoDB | gitignored |
| `/Volumes/downloads` | `/mnt/downloads` | download destination, shared with all 4 *arr apps | SMB share — see known issue |

## Dependencies

- **Depends on:** nothing internal.
- **Depended on by:** Sonarr, Sonarr 4K, Radarr, Radarr 4K (download client), Unpackerr (extracts archives from here), Homepage (status widget).

## Credentials & Secrets

WebUI login: username `kparton`; the password is a PBKDF2 hash on disk (`qBittorrent.conf`, PBKDF2-HMAC-SHA512, 100,000 rounds). It **can't be recovered**, only checked against the hash or reset. The authoritative copy is Infisical `QBITTORRENT_PASSWORD`, **corrected 2026-10-11**: the old value didn't match, and nobody noticed because the localhost-auth bypass (below) let every client in regardless. It was replaced with the value Sonarr held, which was verified against the hash. Who logs in, and with what (checked 2026-10-11 by comparing against the hash, yes/no only):
- ✅ Sonarr, Sonarr 4K, Radarr, Radarr 4K, Prowlarr: their own stored copy, correct. Prowlarr's client host was also stale (`10.10.0.130`) and was fixed 2026-10-11.
- ✅ Homepage widget (`HOMEPAGE_VAR_QBITTORRENT_PASSWORD`) and Mylar3: refreshed from Infisical 2026-10-11.
- ❌ n8n workflow 14's "qBittorrent Login" node: an inline, stale password, which is **also in the public repo** (see `architecture/known-issues.md`). Needs moving to an n8n credential.

## External Access

NPM proxy host `downloads.kodyparton.com` forwards to `192.168.178.69:30024` — fixed 2026-08-27 (was pointed at a dead host `10.10.0.130`, same class of stale-migration issue n8n had).

## Backups

Not covered by workflow 03 — qBittorrent has no "backup" in the traditional sense, its `BT_backup/` directory is live torrent session/resume state, not a discrete backup artifact, so it's deliberately excluded from backup verification.

## Automation

- **02 - Docker Drift Detection**
- **09 - Mount Health Self-Healer** — inactive (found 2026-08-29, was never actually turned on) and now moot regardless: `/mnt/downloads` is a native CIFS volume as of 2026-08-29, not a host-passthrough mount, so the ENOENT-drop failure mode this workflow existed for can no longer happen here.
- **14 - Weekly Media Server Digest** — pulls weekly upload/download totals. **Its qBittorrent login fails since 2026-10-11** (stale inline password, previously hidden by the auth bypass), so the qBittorrent part of the digest is missing until the node uses a credential.
- Unpackerr polls this instance to extract completed downloads.

## Known Issues / Gotchas

- **Was reachable from the internet with no password until 2026-10-11.** "Bypass authentication for clients on localhost" (`WebUI\LocalHostAuth=false`) was on. Behind OrbStack and NPM **every client looks local**, so the bypass applied to everyone, including the internet via the WAN port-forward and `downloads.kodyparton.com`: anonymous `GET /api/v2/app/preferences` → 200 through the WAN IP, even with a bogus cookie. That's full control, including "run external program on completion", which means command execution. **Fixed:** bypass off (`bypass_local_auth=false`). Anonymous requests now get 403 from the LAN and through the WAN. Every client was checked before switching (see Credentials). **Never turn it back on**, and don't use the subnet whitelist as a substitute: the addresses all look local, so it would whitelist the internet too.
- **The ban is shared by every client.** Defaults are 5 failed logins → 3600 s ban per IP, and all clients (and NPM's visitors) arrive from the same OrbStack address. One misconfigured client, or an internet brute-forcer through NPM, can lock **every** app out for an hour. Check new clients' credentials against the hash (yes/no) before pointing them here.
- **qBittorrent 5.x login:** `POST /api/v2/auth/login` returns **204** with no body, and the session cookie is **`QBT_SID_30024`**, not `SID`. Scripts checking for `"Ok."` or `SID` will misjudge a good login.
- **The *arrs' download-client "Test" fails on the share-limit action**, not on login: "unable to perform Completed Download Handling … Share Ratio Limiting … Remove". Global limits are ratio 2 / 25,160 min, and the action is "remove torrent and files". Imports normally finish long before that. Switching the action to Pause would satisfy the check but keep files on the NAS. Kody's call.
- **Categories:** `tv-sonarr`, `tv-sonarr-4k`, `radarr`, `radarr-4k`, `books`, `games`, `prowlarr`, and **`comics`** (Mylar3, `/mnt/downloads/comics`, added 2026-10-11), each saving to `/mnt/downloads/<type>`.
- ~~Same SMB-passthrough mount fragility as the *arr apps~~ — resolved 2026-08-29. `/mnt/downloads` is now a native Linux CIFS volume (`nas_downloads`), mounted directly by Docker inside OrbStack's VM, no macOS host passthrough involved. See `docs/architecture/known-issues.md`.
- Runs under `network_mode: host`, not the usual bridge network — this is intentional for torrenting port forwarding, but means it doesn't appear on any docker-compose project network and can't be reached by container name from other containers, only via the host's LAN IP.

## Change Log

- `2026-10-11` — **Closed unauthenticated internet access** (localhost-auth bypass off) after verifying every client's password against the hash. Infisical's stale `QBITTORRENT_PASSWORD` was corrected, and Homepage and Mylar3 refreshed from it. Added the `comics` category for Mylar3. Found n8n workflow 14's stale inline password (also in the public repo) and Prowlarr's stale `10.10.0.130` client host.
- `2026-08-24` — Doc created.
