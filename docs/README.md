# Homelab Documentation

Documentation for the `docker_homelab` stack — a Mac Mini running ~22 self-hosted services under Docker Compose (via OrbStack), automated by n8n.

## Start here

- **[Architecture Overview](architecture/overview.md)** — service dependency map, port map, domain/reverse-proxy map, data flow.
- **[Automation Map](architecture/automation.md)** — every n8n workflow, what it touches, what it's allowed to change automatically.
- **[Second Brain](architecture/second-brain.md)** — the Discord-native local-LLM knowledge assistant: how it works, how to teach it things, setup steps.
- **[Known Issues](architecture/known-issues.md)** — open problems and their status, resolved-issue changelog.

## Per-service docs

One file per running container in [`containers/`](containers/), each following the same [template](templates/container.md): quick facts, volumes, dependencies, credentials, external access, backups, related automation, known gotchas, and a change log.

| Service | Doc |
|---|---|
| Sonarr | [containers/sonarr.md](containers/sonarr.md) |
| Sonarr 4K | [containers/sonarr-4k.md](containers/sonarr-4k.md) |
| Radarr | [containers/radarr.md](containers/radarr.md) |
| Radarr 4K | [containers/radarr-4k.md](containers/radarr-4k.md) |
| Prowlarr | [containers/prowlarr.md](containers/prowlarr.md) |
| qBittorrent | [containers/qbittorrent.md](containers/qbittorrent.md) |
| Overseerr | [containers/overseerr.md](containers/overseerr.md) |
| Tautulli | [containers/tautulli.md](containers/tautulli.md) |
| Huntarr | [containers/huntarr.md](containers/huntarr.md) |
| Audiobookshelf | [containers/audiobookshelf.md](containers/audiobookshelf.md) |
| LazyLibrarian | [containers/lazylibrarian.md](containers/lazylibrarian.md) |
| Unpackerr | [containers/unpackerr.md](containers/unpackerr.md) |
| Watchtower | [containers/watchtower.md](containers/watchtower.md) |
| n8n | [containers/n8n.md](containers/n8n.md) |
| Trilium | [containers/trilium.md](containers/trilium.md) |
| Nginx Proxy Manager | [containers/nginx-proxy-manager.md](containers/nginx-proxy-manager.md) |
| Homepage | [containers/homepage.md](containers/homepage.md) |
| Vikunja | [containers/vikunja.md](containers/vikunja.md) |
| Ollama | [containers/ollama.md](containers/ollama.md) |
| Qdrant | [containers/qdrant.md](containers/qdrant.md) |
| Brain Bot | [containers/brain-bot.md](containers/brain-bot.md) |

## Keeping this updated

This isn't a one-time snapshot — it's meant to track the real state of the stack. Whenever a service's `compose.yml`, ports, mounts, credentials, or automation coverage changes, its doc in `containers/` and the relevant map in `architecture/` get updated in the same pass as the change itself, with a dated entry in that doc's Change Log. New services get a new doc from the template before being considered "done."
