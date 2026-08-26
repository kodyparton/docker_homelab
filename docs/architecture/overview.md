# Homelab Architecture Overview

Everything runs as Docker Compose services on a single Mac Mini (`192.168.178.69`) via OrbStack, one service directory per app at the repo root, each with its own `compose.yml`. Media libraries and downloads live on a UniFi Drive NAS (`192.168.178.38`), mounted via SMB on the macOS host and passed through into containers as bind mounts.

## Service Map

```mermaid
flowchart LR
    subgraph Indexing
        Prowlarr
    end
    subgraph "Media Management"
        Sonarr
        SonarrHD["Sonarr 4K"]
        Radarr
        RadarrHD["Radarr 4K"]
    end
    subgraph Download
        qBittorrent
        Unpackerr
    end
    subgraph Requests
        Overseerr
    end
    subgraph Stats
        Tautulli
        Plex["Plex (external, not in repo)"]
    end
    subgraph Automation
        Huntarr
        n8n
        Watchtower
    end
    subgraph "Access & Dashboard"
        NPM["Nginx Proxy Manager"]
        Homepage
    end
    subgraph Personal
        Trilium
        Vikunja
        LazyLibrarian
        Audiobookshelf
    end
    subgraph "Second Brain"
        BrainBot["Brain Bot"]
        Ollama
        Qdrant
    end

    Prowlarr --> Sonarr
    Prowlarr --> SonarrHD
    Prowlarr --> Radarr
    Prowlarr --> RadarrHD
    Sonarr --> qBittorrent
    SonarrHD --> qBittorrent
    Radarr --> qBittorrent
    RadarrHD --> qBittorrent
    qBittorrent --> Unpackerr
    Unpackerr --> Sonarr
    Unpackerr --> Radarr
    Huntarr --> Sonarr
    Huntarr --> Radarr
    Overseerr --> Sonarr
    Overseerr --> Radarr
    Plex --> Tautulli
    NPM --> n8n
    NPM --> Overseerr
    NPM -.-> qBittorrent
    NPM -.-> Homepage
    n8n -.-> Sonarr
    n8n -.-> Radarr
    n8n -.-> Prowlarr
    n8n -.-> Overseerr
    n8n -.-> Tautulli
    n8n -.-> qBittorrent
    Watchtower -.-> Sonarr
    Watchtower -.-> Radarr
    Watchtower -.-> Prowlarr
    BrainBot --> n8n
    n8n --> Ollama
    n8n --> Qdrant
```

Solid arrows are functional dependencies (data/API calls the app needs to work). Dotted arrows are n8n/Watchtower/NPM reaching in from outside — monitoring, automation, or routing rather than core function.

## Port Map

| Service | Host Port | Container Port | Notes |
|---|---|---|---|
| NPM (HTTP) | 80 | 80 | |
| NPM (HTTPS) | 443 | 443 | |
| NPM (Admin) | 81 | 81 | |
| Prowlarr | 9696 | 9696 | |
| n8n | 5678 | 5678 | |
| Trilium | 8080 | 8080 | |
| Homepage | 3000 | 3000 | |
| Overseerr | 30023 | 5055 | |
| qBittorrent WebUI | 30024 | — | `network_mode: host`, no port mapping |
| qBittorrent torrenting | 50415 | — | `network_mode: host` |
| Radarr | 30025 | 7878 | |
| Sonarr | 30027 | 8989 | |
| Sonarr 4K | 30030 | 8989 | |
| Radarr 4K | 30031 | 7878 | |
| LazyLibrarian | 30032 | 5299 | fixed 2026-08-17, was misconfigured as 30032:30032 |
| Audiobookshelf | 30033 | 30033 | |
| Vikunja | 30037 | 3456 | |
| Tautulli | 30035 | 8181 | |
| Huntarr | 30036 | 9705 | |
| Ollama | 11434 | 11434 | LAN only, no auth — do not expose publicly |
| Qdrant | 6333 | 6333 | LAN only, no auth — do not expose publicly |
| Infisical | 30034 | 8080 | LAN only, real auth (unlike Ollama/Qdrant) but holds secrets — conservative default |

`brain-bot` has no listening port — outbound only (Discord Gateway + calls to n8n).

Convention: LAN-only services generally live in the `300xx` range. `30034` (formerly a gap) is now Infisical.

## Domain / Reverse Proxy Map

All via Nginx Proxy Manager (`nginx-app-1`), certs via Let's Encrypt DNS-01 through Cloudflare — a single wildcard cert (`*.kodyparton.com`) covers every subdomain, so new subdomains don't need a new cert issuance, just a new proxy host reusing the existing certificate.

| Domain | Forwards to | Status |
|---|---|---|
| `n8n.kodyparton.com` | `192.168.178.69:5678` | working |
| `request.kodyparton.com` (Overseerr) | `192.168.178.69:30023` | working |
| `downloads.kodyparton.com` (qBittorrent) | `10.10.0.130:30024` | **broken — dead host, needs manual fix in NPM UI** |
| `home.kodyparton.com` (Homepage) | `192.168.178.69:3000` | **not yet created — needs manual DNS + NPM steps, see known-issues.md** |

`home.kodyparton.com` is intentionally different from the others: its Cloudflare DNS record should be set to **DNS only** (not proxied), so it resolves to a private LAN IP that's simply unreachable from outside the home network — that's the entire mechanism making it "internal only," no VPN or firewall rule required.

## Data Flow (typical request lifecycle)

1. Request comes in via Overseerr (public, `request.kodyparton.com`) or is added directly in Sonarr/Radarr.
2. Sonarr/Radarr search via Prowlarr's aggregated indexers.
3. Grab sent to qBittorrent, which downloads to the shared `/Volumes/downloads` SMB share.
4. Unpackerr extracts any archive qBittorrent can't hand off directly.
5. Sonarr/Radarr import the finished file into the library (`/Volumes/media/...`).
6. Huntarr periodically re-triggers missing/upgrade searches in the background.
7. Plex (external) picks up new library files; Tautulli records what gets watched.

## Host Notes

- Container runtime is **OrbStack**, not Docker Desktop.
- Media/download storage is a UniFi Drive NAS, SMB-mounted on the macOS host and passed through OrbStack's VM into containers — this passthrough is the root cause of the mount-drop issue documented in `known-issues.md` and self-healed by n8n workflow 09.
- OrbStack's VM memory is capped at **12GB** out of this Mac's 16GB total (`orb config set memory_mib 12288`) — raised from the 8GB default after real OOM-kills in the `ollama` container (see `docs/containers/ollama.md`). Changing this restarts every container on the host (`orb stop && orb start`); all come back automatically via `restart:unless-stopped`.
