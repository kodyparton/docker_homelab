# Stack Review — 2026-08-26

A full pass over every running service: resource usage, actual activity vs. documented purpose, and whether anything is genuinely redundant. Grounded in real data pulled from each container (`docker stats`, API stats endpoints, logs) rather than assumptions.

## The "reduce redundant applications" question — honest conclusion

Went looking for a service to consolidate or remove and didn't find one. Every service in this stack does something the others don't:

- Sonarr/Radarr (+ 4K variants) — different content types and quality tiers, not overlapping.
- Prowlarr — shared indexer management, single instance by design.
- Overseerr — request/discovery layer, distinct from Sonarr/Radarr's acquisition layer.
- LazyLibrarian (ebooks) vs. Audiobookshelf (audiobooks/podcasts) — different media types.
- Trilium (notes, second-brain `note` intent) vs. the separate Obsidian vault (Kody's other, pre-existing second brain) — genuine conceptual overlap (both are note systems), but deliberately serve different assistants with an explicit no-cross-write boundary (see `second-brain.md`) — not redundant in the "delete one" sense, just two systems that happen to both be note-shaped.
- Huntarr vs. Sonarr/Radarr's own search — complementary (aggressive missing/upgrade hunting vs. baseline RSS sync), not overlapping — see below, this one just wasn't actually working.
- Unpackerr — does something Sonarr/Radarr can't do natively (archive extraction).

**What was actually wrong wasn't redundancy — it was two services quietly not working at all** despite running 24/7 and consuming resources. That's arguably a better finding: fixing them recovers value from cost you were already paying, rather than just removing cost.

## What was found and fixed

### Huntarr — non-functional since deployment (Jan 2026), now fixed

`GET /api/stats` showed `hunted: 0, upgraded: 0` for every app, unconditionally — proof it had never successfully found or upgraded a single item across its entire runtime. Root cause: both its Sonarr and Radarr instance configs had **empty `api_key`/`api_url`** — Radarr's address was even set to `http://localhost:7878`, which doesn't resolve to anything from inside the Huntarr container. It also only had one instance each configured, missing the 4K tiers entirely, despite the existing docs claiming it covered all 4 *arr instances.

Fixed by discovering the actual save endpoint (`POST /api/settings/<app>` — `/api/settings` itself is read-only and returns 405 on any write), wiring in real API keys (now sourced from Infisical) and correct URLs for all four instances (Sonarr, Sonarr 4K, Radarr, Radarr 4K). Verified immediately: found 428 real missing episodes, triggered a real season search, `hunted` count moved from 0 to 3 within a minute.

One debugging dead-end worth remembering: Huntarr's logs show `Loaded schedules: {'global': 0, 'sonarr': 0, ...}` on every cycle, which reads like "hunting disabled." It isn't — hunting worked fine with those all still at 0. That's an unrelated scheduling-window feature, not a kill switch. Don't be misled by it again.

### Unpackerr — broken since setup, wrong mount entirely

Its downloads-folder mount (`~/mnt/downloads`) was not an alias for the real share — it was a completely different, empty local directory. Sonarr/Radarr place completed downloads at `/Volumes/downloads`; Unpackerr could never see them, so every completed item failed forever with "no such file or directory," retried on a loop. The wrong directory also silently accumulated 55MB of Unpackerr's own rotated log files, because `UN_LOG_FILE` was *also* pointed inside that same broken path.

Fixed: mount corrected to `/Volumes/downloads:/mnt/downloads` (matching every other service), `UN_LOG_FILE` removed in favor of plain `docker logs` output, stale log files deleted. Verified live — errors stopped immediately, previously-stuck items were found correctly on restart.

### Housekeeping

- `docker image prune -a` reclaimed 1.6GB of unused image layers.
- Both fixes above freed real disk (55MB of misplaced logs) and, more importantly, real *functionality* that had been silently missing for months.

## New addition: Uptime Kuma

Real gap, not a "nice to have": this stack has failure *alerting* (workflow 27 polls the second brain's health every 15 min, workflow 17's `!status` gives an on-demand snapshot) but nothing gives a visual, historical "what's my uptime % been for the last 30 days" view for anything. Uptime Kuma (MIT licensed, `uptime-kuma/compose.yml`, port `30038`) fills that specific gap without overlapping the existing Discord-based alerting. Deployed and healthy; admin account creation and monitor configuration are next (same "you create the first account" pattern as Vikunja/Trilium/Infisical), see `docs/containers/uptime-kuma.md`.

## Considered and deliberately not built

- **Offsite/secondary backup destination** — real gap (every backup in this stack, including Infisical's own, lands on the same physical disk as the originals) but explicitly deferred this pass, not chosen when offered.
