# Candidate Services — Research, Not Yet Built

Researched 2026-08-26 at Kody's request. **Nothing here is implemented.** Each entry is judged against this specific homelab's real constraints, not general "best self-hosted app" lists.

## The constraints these have to fit

Measured, not assumed:

| Constraint | Reality | What it rules out |
|---|---|---|
| **Boot disk** | **11GB free** of 228GB — Docker *images* live here | Anything with a multi-GB image stack, without cleanup first |
| **CPU** | Ollama owns it. Measured 0.49 tok/s when a 3rd model competed | Anything doing heavy continuous ML inference |
| **RAM** | 12GB OrbStack VM, Ollama holds ~5GB | Anything wanting 6GB+ on its own |
| **Architecture** | **arm64** (M1) | Anything without ARM64 images |
| **NAS** | 23TB free | Nothing — bulk data has plenty of room |
| **Remote access** | Tailscale already installed on host | Any "remote access" tool — already solved |

The binding constraint is **boot disk**, not the NAS. Bulk data goes to `/Volumes/media`; container images don't get that choice.

---

## Tier 1 — fills a gap I can see actual evidence for

### 1. Immich — photo & video backup
**The highest-value item on this list, with a real caveat.**

You have kids (Wild Kratts, Lion Guard, Minions in the library), a 23TB NAS, and 6.4GB of Apple Photos analysis cache I cleared yesterday — meaning photos currently live in Apple's ecosystem with no self-hosted copy. Immich is the mature Google Photos replacement: mobile auto-backup, face grouping, shared albums, timeline.

- v3.1.0 stable as of Aug 2026; native ARM64.
- **Honest caveat**: docs say 6GB RAM min / 8GB recommended, and its ML worker (face recognition) is exactly the kind of continuous CPU load that already crippled Ollama when I tested a vision model — I measured 0.49 tok/s under that contention. Face recognition on ARM CPU without GPU is documented as impractical past a few thousand photos.
- **Verdict**: worth doing, but plan to **disable or heavily throttle the ML features** and treat it as backup + browsing rather than smart search. Or accept that ML runs overnight when nobody's talking to the second brain.

### 2. Paperless-ngx — document management
Scan/ingest bills, warranties, tax docs, school paperwork; OCR makes them full-text searchable forever. For a family this quietly becomes indispensable.

- Native ARM64. Can run on SQLite instead of Postgres to stay light.
- OCR is CPU-intensive but bursty (only when documents arrive) — far friendlier to your Ollama contention than Immich's continuous ML.
- **Strong second-brain tie-in**: it has a REST API, so the brain could answer "when does the dishwasher warranty expire?"
- **Verdict**: best value-to-resource ratio on this list.

### 3. Beszel — lightweight resource monitoring
You had an actual OOM kill on Ollama that took real debugging to find. Uptime Kuma (just added) tells you *up or down* — it won't show you memory creeping up over a week.

- Agent uses **under 10MB RAM**, vs 400-700MB for a Prometheus + Grafana + cAdvisor stack.
- Per-container CPU/RAM/disk/network history, auto-discovered via Docker socket — which you already expose read-only for Homepage.
- **Verdict**: near-zero cost, directly addresses a failure you've already hit. Easiest yes here.

### 4. Vaultwarden — password manager for *human* logins
This is **not** redundant with Infisical. When you asked about a credential manager I steered you to Infisical specifically because it's built for API keys and service secrets. Vaultwarden covers the other half: browser-autofill passwords, 2FA seeds, secure notes, family sharing. Different job.

- Tiny (~200MB image, minimal RAM), ARM64 native, Bitwarden-client compatible.
- **Verdict**: yes, if you're not already happy with 1Password/iCloud Keychain. Worth asking yourself that first.

---

## Tier 2 — strong fit, clear use, lower urgency

### 5. FreshRSS — RSS reader
Your habit pillars include **Learning** ("added a note to Research/ or intentional reading"). FreshRSS gives that a source, and — more interestingly — it has an API, so n8n could pipe interesting articles straight into the second brain's memory. That turns passive reading into something the brain can recall later.

### 6. linkding — bookmark manager
Tiny (~100MB), fast, tag-based. Same second-brain angle as FreshRSS: save a link, have the brain able to answer "what was that article about X?" Pairs naturally with #5.

### 7. Navidrome — music streaming
You have TV, movies, books, audiobooks, podcasts — **music is the one media type missing**. Navidrome is lightweight (Go, tiny footprint), Subsonic-compatible so it works with a lot of good mobile clients.
- Only worth it if you actually have a music library to serve; if you're happy on Spotify, skip.

### 8. Mealie — recipes & meal planning
Recipe storage with URL import, meal planning, auto-generated shopping lists. Family-practical. ARM64 native, modest footprint.
- Second-brain tie-in: "what are we having Thursday?" is answerable via its API.

### 9. Forgejo (or Gitea) — private git hosting
Your homelab repo is **public on GitHub** — which has already caused one real problem (the qBittorrent password sitting in public history). A private local git host gives you somewhere for things that shouldn't be public, without paying for private GitHub or self-censoring.
- Lightweight, ARM64 native. Also a genuine backup of your repo independent of GitHub.

---

## Tier 3 — worth knowing about, more situational

### 10. Dozzle — live Docker log viewer
~30MB, no database, just a clean web UI for `docker logs` across all containers. You and I have both spent a lot of this project reading logs via CLI. Cheap quality-of-life.

### 11. Stirling PDF — PDF toolbox
Merge, split, sign, OCR, convert — entirely local, nothing uploaded to a sketchy website. Pairs well with Paperless-ngx.

### 12. Piper — text-to-speech
You already have **Whisper for speech-to-text** (voice messages in). Piper is the reverse: it'd let the second brain *speak* replies. Fast, ARM-friendly, small models. A genuinely novel capability rather than another CRUD app — and it closes the loop on a voice interface you've half-built already.

### 13. Actual Budget — personal finance
Envelope budgeting, local-first, no bank credentials required (manual or CSV import).
- **Boundary note**: your `SOUL.md` says the assistant should never access financial data. That's a rule about *me*, not about what you self-host — but I'd want it explicitly confirmed that I stay out of this one's data even if it's running. Flagging rather than assuming.

### 14. AdGuard Home — network-wide ad/tracker blocking
DNS-level blocking for every device. **Uncertainty worth stating**: you're on UniFi, which has its own content-filtering features I haven't inspected. This may be partly redundant — I'd check what your UniFi setup already does before adding it.

### 15. Home Assistant — home automation
The obvious "next big thing" for most homelabs, but I have **no evidence you own smart-home devices** — nothing in this repo or your setup suggests it. Listed for completeness; ignore unless you actually have hardware to control.

---

## If I had to pick three

1. **Beszel** — costs almost nothing, fixes a monitoring gap you've already been bitten by.
2. **Paperless-ngx** — highest life-value per resource consumed, and the CPU load is bursty rather than constant.
3. **Immich** — biggest quality-of-life win, but only with ML throttled, and ideally after freeing boot-disk space.

## What to do before adding any of these

**The boot disk is at 11GB free.** Every new service's image lands there. Immich alone is a multi-container stack. Before adding two or three of these, it's worth a real cleanup pass — the 3.1TB of 4K duplicates identified in `plex-cleanup-design.md` is NAS space rather than boot disk, so it doesn't help here; this needs its own look at what's eating the boot volume.
