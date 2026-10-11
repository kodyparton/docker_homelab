# AdGuard Home

Network-wide DNS resolver with ad/tracker blocking. **Free and open source (GPL-3.0) — no paid tier, no limits.** (Distinct from AdGuard's paid *AdGuard DNS* cloud service and browser products, which this is not.)

Deployed 2026-08-27 to solve a specific problem, with ad blocking as a genuine bonus: the ISP/router path silently drops DNS answers containing private IPs (see `known-issues.md`), which made `home.kodyparton.com` and `auth.kodyparton.com` unreachable by name. A resolver on the LAN answers those itself, so the response never crosses the filtering boundary.

## Quick Facts

| | |
|---|---|
| **Image** | `adguard/adguardhome:latest` (v0.107.79 at deploy) |
| **Container name** | `adguard` |
| **Compose file** | `adguard/compose.yml` |
| **Port(s)** | `53:53/udp`, `53:53/tcp` (DNS), `30043:80` (web UI) |
| **Local URL** | `http://192.168.178.69:30043` |
| **Public URL** | none — LAN only, deliberately |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `adguard/conf` | `/opt/adguardhome/conf` | `AdGuardHome.yaml` — all settings **incl. the admin bcrypt hash** | gitignored |
| `adguard/work` | `/opt/adguardhome/work` | query log, statistics, downloaded blocklists | gitignored |

## Dependencies

- **Depends on:** nothing.
- **Depended on by:** every device configured to use it for DNS. Nothing in Docker depends on it — containers use Docker's internal DNS.

## Credentials & Secrets

Admin user `admin`; password in Infisical as `ADGUARD_ADMIN_PASSWORD` — **change it**. Stored bcrypt-hashed in `conf/AdGuardHome.yaml`, which is gitignored for that reason.

## Configuration worth knowing

- **Upstreams are DNS-over-TLS** (`tls://1.1.1.1`, `tls://1.0.0.1`). Deliberate on two counts: encrypted queries can't be inspected or filtered by the ISP/router path (which is the whole bug being worked around), and the ISP no longer sees every lookup.
- **DNS rewrites** map the five `*.kodyparton.com` hostnames to `192.168.178.69`, so they resolve locally even if upstream is unreachable.
- Blocklists: AdGuard DNS filter + AdAway (~185k rules at deploy).

## External Access

None. LAN only — an open DNS resolver on the internet is an abuse vector.

## Backups

Not yet in workflow 03. Low stakes: `conf/AdGuardHome.yaml` is the only thing worth keeping and it's small and reproducible from this doc.

## Automation

None yet.

## Known Issues / Gotchas

- **Devices must be told to use it.** Installing it changes nothing until clients point at `192.168.178.69` for DNS. Ideally set once in the router's DHCP settings; on a locked-down ISP router that may not be possible, in which case configure per-device.
- **Found 2026-08-29: the Mac Mini running this whole stack wasn't even using AdGuard itself.** Discovered while wiring up 17 new proxy hosts — `dig` with no explicit server returned nothing for any `*.kodyparton.com` name; `scutil --dns` showed the active resolver was still the ISP's own DNS (an IPv6 address under `chello.nl`, the same rebinding-affected path this container exists to route around). All the rewrites/proxy hosts were correct the whole time, they just weren't being consulted for ordinary browsing. Fixed with `networksetup -setdnsservers Ethernet 192.168.178.69 1.1.1.1` (and the same for Wi-Fi, for resilience if this Mac ever switches interfaces) — `1.1.1.1` as secondary so DNS still works if the AdGuard container itself is ever down. Verified: a plain `dig sonarr.kodyparton.com` (no explicit server) now resolves correctly. **Router-level DHCP was not attempted** — no stored credentials for it, and it's an ISP-supplied Sagemcom that may not expose a custom-DNS option; tracked as a task for Kody to try himself. Every *other* device on the LAN (phones, laptops) still needs this same per-device fix, or the router-level fix, to actually benefit.
- **Single point of failure once adopted.** If this container is down and it's your only DNS server, name resolution stops for everything configured to use it. Set a secondary DNS (e.g. `1.1.1.1`) on clients, or accept the dependency knowingly.
- **`rewrites` in a hand-written `AdGuardHome.yaml` need `enabled: true` per entry.** Without it they are silently ignored — the config loads, the UI shows nothing, and no error appears anywhere. This was hit during setup: the domains appeared to work, but only because the DoT upstream was resolving them; the rewrites were doing nothing. Verified with `GET /control/rewrite/list` returning `[]`. Adding them through the API sets the field correctly.
- **AdGuard rewrites its own `AdGuardHome.yaml` as it shuts down**, so editing that file while the container is running gets silently overwritten on the next restart. If you must edit it by hand, `docker stop adguard` first, then edit, then `docker start adguard` — accepting that LAN DNS is down for those few seconds. The API (`POST /control/rewrite/add`) needs no restart and no outage, and is the better path; `scripts/add_device_proxy_hosts.py` uses it by default and keeps the file method behind `--dns-method=file` for when the admin password isn't available.
- Port 53 must be free on the host. It was here; macOS's mDNSResponder uses 5353, not 53.

## Change Log

- `2026-10-11` — Added rewrite `comics.kodyparton.com` → `192.168.178.69` (YACReader) through the API with no restart, using `do_dns_api()` from `scripts/add_device_proxy_hosts.py` (credential from Infisical). Verified with `dig @192.168.178.69`.
- `2026-08-30` — Added rewrites for `nas.kodyparton.com` (UniFi UNAS Pro) and `ziggo.kodyparton.com` (Ziggo modem), both → `192.168.178.69`, via `scripts/add_device_proxy_hosts.py`, which reads `ADGUARD_ADMIN_PASSWORD` from Infisical. 24 rewrites total.
- `2026-08-27` — Built to work around ISP/router DNS rebinding protection. Rewrites for the 5 `*.kodyparton.com` hosts, DoT upstreams, 2 blocklists.
