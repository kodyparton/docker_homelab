# Second Brain Tagging

A bounded, documented tag vocabulary for everything stored in the `second_brain` Qdrant collection — added 2026-08-25 so search/recall/journal generation can filter by what actually matters instead of scanning everything at once, and so tags stay consistent instead of sprawling into one-off strings over time.

**Scope note**: this only tags what's stored in this project's own memory (Qdrant). It deliberately does **not** touch `~/Obsidian/KodyBrain` — that vault has its own dedicated assistant and its own organizational conventions, and this second brain has been read-only into it since 2026-08-25 for exactly that reason (see `second-brain.md`). Content synced *from* the vault gets a `domain: obsidian` tag here, in this project's own database, same as everything else — nothing is written back.

## Two payload fields, both on every point

- **`domain`** — exactly one value: `homelab`, `personal`, `obsidian`, or `test`.
- **`tags`** — zero to three values, drawn only from the fixed list below. Not a free-form field — anything outside this list gets dropped rather than stored, on both the backfill script and the live workflow, so the vocabulary can't quietly drift.

## Domains

| Domain | What it covers |
|---|---|
| `homelab` | This repo's own documentation — `docs/containers/*`, `docs/architecture/*`, templates, README |
| `personal` | Real facts/conversations/tasks/notes from Kody, via Discord |
| `obsidian` | Content synced read-only from `~/Obsidian/KodyBrain` |
| `test` | Development/testing artifacts — self-test workflow runs, live-verification messages sent while building a feature. Excluded from what the daily journal and weekly digest treat as real content. |

## Topic tags

| Tag | Meaning |
|---|---|
| `media` | Sonarr/Radarr/Prowlarr/Overseerr/Tautulli/qBittorrent/LazyLibrarian/Audiobookshelf/Unpackerr |
| `automation` | n8n itself, workflow logic |
| `ai` | Ollama, Qdrant |
| `networking` | NPM, DNS, external access |
| `productivity` | Vikunja, Trilium |
| `dashboard` | Homepage |
| `ops` | Backups, monitoring, known issues, watchtower |
| `second-brain-system` | This second brain's own architecture/setup (as opposed to a topic *stored in* it) |
| `identity` | Who Kody is — preferences, standing facts about him |
| `dates` | Birthdays, deadlines, anything date-anchored |
| `health` | Health/fitness related |
| `work` | Work-related |
| `preferences` | Stated preferences/decisions |
| `habits` | Habit tracking |
| `memory` | Meta — things about what the brain itself remembers |
| `journal` | Daily journal / daily notes |
| `tasks` | Task/to-do related content |
| `credentials` | Passwords, codes, access info |

## How it's applied

- **Existing content**: `scripts/tag_second_brain.py` — a one-time (or re-runnable) backfill. Rule-based for anything with a `source` path (deterministic lookup from file path to domain+tags, no LLM, instant). LLM-based for Discord-originated content (facts/conversations/photos/journal entries) — one batched Ollama call tags everything in a single pass rather than one call per item, since that would be far slower on this CPU-only hardware.
- **New content**: `Classify Intent` (workflow 18) now also returns `tags` as part of its normal JSON output — no extra LLM call, it rides along with the classification pass that already has to read the message. `Parse Intent` validates the tags against the fixed list, dropping anything invalid. Messages that go through the keyword fast-path (skipping the classifier) get a small deterministic tag set based on which pattern matched, so tagging doesn't cost them their speed. `domain` is set automatically: `test` when the message came from the self-test workflow (`author_id: "self-test"`), `personal` otherwise.
