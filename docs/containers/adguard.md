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
- **Single point of failure once adopted.** If this container is down and it's your only DNS server, name resolution stops for everything configured to use it. Set a secondary DNS (e.g. `1.1.1.1`) on clients, or accept the dependency knowingly.
- **`rewrites` in a hand-written `AdGuardHome.yaml` need `enabled: true` per entry.** Without it they are silently ignored — the config loads, the UI shows nothing, and no error appears anywhere. This was hit during setup: the domains appeared to work, but only because the DoT upstream was resolving them; the rewrites were doing nothing. Verified with `GET /control/rewrite/list` returning `[]`. Adding them through the API sets the field correctly.
- Port 53 must be free on the host. It was here; macOS's mDNSResponder uses 5353, not 53.

## Change Log

- `2026-08-27` — Built to work around ISP/router DNS rebinding protection. Rewrites for the 5 `*.kodyparton.com` hosts, DoT upstreams, 2 blocklists.
