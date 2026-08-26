# Plex "Leaving Soon" Cleanup — Design & Feasibility

**Status: design only, nothing built, nothing deleted.** Written 2026-08-26 at Kody's request, explicitly ahead of implementation so items can be flagged for keeping first.

Every number below came from querying the live Plex/Radarr/Sonarr/Overseerr/Tautulli APIs read-only, not from estimation.

## The short version

All the technical pieces exist and this is buildable. **The problem isn't feasibility — it's that the rules as stated would flag ~85% of the library on day one.** That's not a reason not to do it, but it does mean the thresholds need revisiting before anything is automated, and it makes the "flag things to keep" step much bigger than it sounds.

## Blast radius under the proposed rules (>90 days unwatched)

| Library | Total | Would enter "Leaving Soon" immediately | % |
|---|---|---|---|
| Movies | 493 | 421 | 85% |
| Movies - 4K | 81 | 78 | 96% |
| TV Shows | 217 | 172 | 79% |
| **Total** | **~791** | **~671** | **~85%** |

Some of what's in that 85%, pulled from the real data:

- The entire **Harry Potter** collection — in the library 1,362 days, never watched.
- **The Mandalorian** — 7 of 16 episodes watched, last touched 1,221 days ago.
- **Parks and Recreation** — 125 episodes, last activity 1,062 days ago.

That's the shape of the problem: a lot of this is *library* (things kept because you want them available), not *backlog* (things to watch or lose). A 90-day timer can't tell those apart, which is exactly why the manual keep-flagging matters.

## Important context: there is no space pressure

The NAS is **44TB total, 21TB used, 23TB free (48%)**. Nothing is close to full.

Worth stating plainly because it changes what "success" means: this can't really be justified as a capacity fix. If the goal is a curated, Netflix-like "watch it or lose it" shelf, that's a perfectly good reason on its own — it's just a different goal with a different risk tolerance than "I'm running out of disk," and the thresholds should be chosen accordingly.

**Separate finding worth acting on regardless**: 78 of the 81 movies in the 4K library also exist in the standard Movies library — the 4K library is almost entirely duplicates, at 3.1TB. Deduplicating that is a bigger, safer, one-time space win than the entire cleanup feature, if space ever does matter.

## Five design problems that need decisions before building

### 1. Never-watched items have no timer to start from
212 of 493 movies have **no `lastViewedAt` at all** — Plex has no record of anyone ever playing them. "Unwatched for 90 days" is undefined for these. The options: fall back to `addedAt` (which is what catches all of Harry Potter), exclude never-watched items entirely, or give them a separate, longer grace period. **This needs your call** — it's the single biggest driver of the 85% number.

### 2. Partially-watched shows are the worst deletion case
The Mandalorian at 7/16 episodes, The Last Thing He Told Me at 7/15. Deleting a show someone is midway through is a worse outcome than deleting one never started. Recommend: any show with `viewedLeafCount > 0` but `< leafCount` gets excluded, or a much longer timer.

### 3. 4K and 1080p copies are tracked separately
78 duplicate titles. Plex treats them as independent items with independent view dates — **watching the 4K copy does not mark the 1080p copy as watched.** A naive implementation would delete whichever copy you don't happen to use, and could delete the 1080p version of something you actively watch in 4K. Any implementation has to match titles across the two libraries and treat a view of either as a view of both.

### 4. Re-requesting a deleted item can silently fail
Your existing **workflow 13 (Smart Overseerr Triage)** auto-*declines* requests for anything available on a streaming service you subscribe to. So the "delete it, request it again if you want it back" path breaks exactly for popular titles — someone re-requests a deleted movie, workflow 13 declines it automatically, and nothing comes back. This needs an explicit exemption: requests for previously-deleted items should bypass the streaming-availability check.

### 5. Tautulli's per-item cache is empty and unused
`get_library_media_info` returns `last_refreshed: null` and zero rows for every section — Tautulli has 2,628 play-history records but has never built its per-item media table. **Recommendation: don't use Tautulli as the data source for this.** Query Plex directly (`lastViewedAt` on each item), which is authoritative, always current, and needs no cache warm-up. Tautulli stays useful for *who* watched *what when*, which matters if you ever want per-user rules.

(Unrelated but noticed: Tautulli's stored `pms_ip` is `10.10.0.130`, a dead host — the same stale address behind the known `downloads.kodyparton.com` issue. It still works because it connects via a `plex.direct` URL, but that IP should be corrected.)

## What the build actually looks like

Assuming the decisions above are settled, four components:

**1. State tracking.** "Entered Leaving Soon on date X" has to persist somewhere — Plex collections alone can't store it. Qdrant already exists and is the natural home (or a small SQLite file). Needs: rating key, library section, date flagged, last-viewed-at when flagged.

**2. The nightly evaluation job** (n8n workflow, matching existing patterns):
- Pull every item from all 4 Plex sections with `lastViewedAt`/`addedAt`
- Skip anything carrying the keep label (see below)
- Cross-reference 4K/1080p duplicates so a view of either counts for both
- Items newly past the stale threshold → add to "Leaving Soon" Plex collection + record the date
- Items in the collection whose `lastViewedAt` has moved since flagging → **remove from collection, clear state** (this is the timer reset, and it's naturally self-correcting)
- Items in the collection past the grace period → hand to the deletion step

**3. The deletion step** — the only destructive part, and where the safeguards go:
- Radarr: `DELETE /api/v3/movie/{id}` with `deleteFiles=true`, plus set `monitored: false` and add an `auto-deleted` tag so it won't re-grab
- Sonarr: same shape for series
- Overseerr: `DELETE /api/v1/media/{id}` so the item can be requested fresh again
- Post a summary to Discord

**4. The keep-flag mechanism** — Plex **labels** are the right tool. They're native, per-item, editable from the Plex UI on any device (web, phone, TV), survive metadata refreshes, and are readable via the API. Currently zero labels exist in the library, so `keep` is unused and unambiguous.

## Safeguards I'd want before this ever deletes anything

Given the 85% number, I would not run this straight through. Recommended sequencing:

1. **Dry-run mode first, for at least one full cycle** — everything runs, the collection populates, Discord reports what *would* be deleted, but the deletion step is disabled. This is the real test of whether the thresholds match your intuition.
2. **A hard cap per run** (e.g. no more than 10 deletions in a night) so a logic bug can't clear the library in one pass.
3. **Kill switch** — one flag that disables deletion, independent of the rest of the workflow.
4. **Deletion log** — reuse the existing `shadow_log` pattern from the second brain: record what was deleted, when, and its metadata, so anything wrongly removed can at least be identified and re-requested.
5. **Start with movies only.** TV has the partial-watch problem and far more per-item complexity; get the simpler case right first.

## What you need to do before implementation

The thing you flagged — flagging keeps — is the blocker, and it's genuinely the biggest task here. Two ways to make it manageable:

**Option A (recommended): invert the default.** Rather than labeling ~671 items to keep, label the much smaller set you're actively willing to lose, and treat everything else as protected until proven otherwise. Slower to reach a clean library, but no chance of losing something you cared about.

**Option B: bulk-label by collection, then refine.** In Plex, multi-select → add label `keep` to obvious permanent-library groups (Harry Potter, Marvel, kids' shows, anything rewatched), then let the dry run surface what's left and refine from there.

Either way I can generate a **candidate list first** — every item that would be flagged, sorted by how long it's been sitting, with its watch state — as a CSV or Discord post, so you can review the actual titles before touching anything. That's probably the right next step, and it's completely read-only.

## Open questions for you

1. **Never-watched items** — protected, or deleted on an `addedAt` timer? (biggest single decision)
2. **Are 90/30 the right numbers** given the 85% result, or should they start much longer — say 365/60 — and tighten later?
3. **Movies only to start, or TV too?**
4. **Should other users' viewing count?** Right now the rule is "anyone watches it, timer resets" — Tautulli shows at least two other users (`carla514` and others) with activity. Confirming this is the intent.
5. **Delete files, or just unmonitor and leave them?** A middle ground exists: stop managing it in Radarr/Sonarr but keep the file, which gets the curation without the irreversibility.
