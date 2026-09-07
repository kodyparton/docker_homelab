# Per-User "Requested By" Collections + Deletion Flagging

**Status: built and live as of 2026-09-04. Collections are populated. Nothing deletes anything.**

Implemented by `scripts/plex_user_collections.py`. Companion to `plex-cleanup-design.md` (the time-based "Leaving Soon" design, still unbuilt) — this one is request-driven rather than staleness-driven.

## What it does

Each Seerr user gets a Plex collection named `Requested by <user>`, containing the things they requested that they have **not yet finished watching**. As they watch, items drain out. When an item has drained from *every* collection it was in, it is **flagged for review** — never deleted.

## Why the obvious rule was rejected

Kody's original framing was "if the item is no longer in anyone's collection, flag for deletion." Measured before building: **627 of 820 library items (76%) have no matching Seerr request at all** — content added directly, added before Seerr, or requested by users who have left. 96% of the 4K movies library is in that bucket. That rule would have flagged three quarters of the library on day one.

This is the same failure `plex-cleanup-design.md` hit ("would flag ~85% of the library on day one"). So eligibility is defined as:

> was in ≥1 user collection at some point **AND** is now in zero

Not "currently in zero collections". An item never requested through Seerr can never drain out of a collection it was never in, so it is permanently excluded. **This is the entire reason the script keeps a SQLite state database** (`~/.local/state/plex_user_collections.sqlite3`) — without persisted membership history the two cases are indistinguishable.

## Verified mechanics

| Question | Answer |
|---|---|
| Seerr → Plex user identity | Native. Seerr `plexId` == Plex `accountID` == Tautulli `user_id`. carla514 is `27962963` in all three. |
| Request → media identity | Join on **`tmdbId`** (100% populated). **Not** `ratingKey` — only 64% populated. |
| Per-user watch state | Tautulli history (2,681 rows), `user_id` + `watched_status` + `rating_key`. |
| Duplicate downloads | **Not a risk, nothing built.** Requests already flow to the same Sonarr/Radarr, which dedupe on TVDB/TMDB id. |
| Writing a real Plex *Watchlist* | **Impossible for an admin.** It is a plex.tv per-account feature needing each user's own token. |
| Per-user *playlists* | **Also impossible.** `POST /playlists/{id}/share` → 404; playlist objects carry no owner/shared fields. Tested, not assumed. |
| Collection membership edits | `PUT /library/sections/{sid}/all?type={1\|2}&id={rk}&collection[0].tag.tag=NAME` to add, `collection[].tag.tag-=NAME` to remove. The `/library/collections/{id}/items` endpoint returns 400 — do not use it. |

## How a user says "I'm done with this"

**Inside Plex, playback is the only user action an admin can observe.** Verified: shared users cannot edit collections or labels (admin-only), and their star ratings and Watchlist live on their own plex.tv account — unreadable with an admin token. So the release signal has to come from Seerr, where every Plex user already has an account.

**Mechanism: a Seerr issue containing `#done`.** The user opens the title in Seerr → *Report Issue* → any type → comment containing `#done`. The script reads `issue.media.tmdbId` + `issue.createdBy.displayName`, drains the item from that user's collection, and records `released_at` in state so closing the issue later cannot resurrect it. Open and closed issues both count.

Chosen because it needs no new infrastructure, no per-user tokens, and Issues are already enabled and in use (`MANAGE_ISSUES` on carla514 and Onumis). **Verified end-to-end 2026-09-04**: a test issue with `#done` was detected, produced exactly one planned removal from the right user's collection, moved the flagged count 25 → 26, and was then deleted and the state row cleared.

Rejected alternative: letting users delete their own Seerr request. Semantically cleaner, but Overseerr/Seerr appears to permit self-deletion only while a request is `PENDING`, not once `AVAILABLE` — which is exactly the state that matters. Not built on, because it was not verifiable without a non-admin login.

## Two bugs found by running it, not by reading it

1. **A single episode drained a whole series.** The first version added the series (grandparent) rating key whenever any episode hit `watched_status == 1` — watching one episode of Ted Lasso marked all 34 done. Fixed: a series counts as watched only when distinct completed episodes ≥ Plex's `leafCount`. Flagged count dropped 29 → 25 (Ted Lasso and Spin City correctly fell off).
2. **"Watched by all requesters" ≠ "disposable."** The first clean run flagged *The Lord of the Rings: The Two Towers*, *Tangled*, *The Croods* and six *My Little Pony* titles — permanent library and kids' content that gets rewatched. Added the `keep` label exclusion that `plex-cleanup-design.md` had already settled on. **Currently 0 items carry the label**, so this protection is inert until Kody applies it.

## Unrequested content

524 library items have no Seerr request behind them. They go to a dedicated **`Unrequested — admin cleanup`** collection, *not* into the admin's own "Requested by" collection — merging them would bury Kody's ~65 genuine requests under 524 unrelated items and destroy that collection's use as a watchlist. Same manual-cleanup goal, without wrecking the feature.

## Awaiting availability

45 requested titles have no Plex item yet — `PROCESSING` (31), `PARTIALLY_AVAILABLE` (18), `PENDING` (6): unreleased, or no torrent found. **No special handling is needed**: the script re-reads Seerr and Plex fresh on every run, so an item is picked up and added to its requester's collection automatically the moment it lands. They are counted in the report so the backlog stays visible.

## Current state (2026-09-04)

15 collections, 688 items:

| Section | carla514 | kaylaparton | Kody.Parton | Onumis |
|---|---|---|---|---|
| TV Shows | 27 | 12 | 19 | 7 |
| Movies | 16 | 28 | 42 | 8 |
| Movies - 4K | — | — | 2 | — |
| TV Shows - 4K | 1 | — | 2 | — |

Plus `Unrequested — admin cleanup`: 135 TV, 300 Movies, 78 Movies-4K, 11 TV-4K = 524.

**25 items flagged for review.** Re-running plans 0 changes (idempotent, safe to schedule).

**Idempotency bug found and fixed 2026-09-04** — worth knowing before touching the parsing: Plex returns titles **HTML-escaped** (`Unrequested &#8212; admin cleanup`, `Tom Clancy&#39;s Jack Ryan`). Matching the raw escaped string against a Python literal never succeeded, so the collection looked empty and the sync re-planned all 524 adds on every run. Fixed with `html.unescape()` on both collection and item titles. Any new title parsing must do the same.

**Note:** the state DB records observations even in `--dry-run` (a `#done` release is written whether or not membership is synced). That is intentional — state tracks what was seen, not what was done — but it means a test release must be cleared from the DB manually, not just deleted in Seerr.

## Scheduling

`scripts/com.kody.plex-user-collections.plist` — a launchd agent running `--apply` every 30 minutes (a no-op run takes ~7s). **Written and validated but NOT installed**, matching the convention set by `com.kody.cifs-volume-healer.plist`. `RunAtLoad` is deliberately `false` so loading the agent cannot immediately mutate collections before you have looked at it.

```
cp scripts/com.kody.plex-user-collections.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kody.plex-user-collections.plist
```

launchd rather than cron: writing to the crontab from a non-interactive session hangs on this Mac (macOS TCC gates the write; `crontab -l` reads fine). The repo already uses launchd agents, so this stays consistent. If you prefer cron, the equivalent line is:

```
*/30 * * * * PATH=/usr/local/bin:/usr/bin:/bin /usr/bin/python3 /Users/kp-srv-01/Documents/docker/scripts/plex_user_collections.py --apply >> /Users/kp-srv-01/Documents/docker/plex_user_collections.log 2>&1
```

The script loads API keys from `homepage/.env` itself (`load_env_file()`), so it needs no environment set up by the scheduler — verified by running it under `env -i`.

## Usage

```
set -a && . homepage/.env && set +a
python3 scripts/plex_user_collections.py            # report only (default)
python3 scripts/plex_user_collections.py --apply    # sync collection membership
python3 scripts/plex_user_collections.py --json     # machine-readable
```

`--apply` only ever edits collection membership. It never deletes media, and there is no flag that makes it do so.

## Open decisions before any deletion happens

1. **Apply `keep` labels first.** With 0 labels set, the flagged list still contains things nobody wants deleted.
2. **kaylaparton has 49 solo requests and 1 completed title** — a watch-driven rule barely fires for her. Worth confirming the model matches real behaviour.
3. **Only 1 of 233 titles was requested by more than one user**, so the multi-requester guard is nearly moot today — but it must stay, since that changes as usage grows.
4. **45 requested titles have no Plex item** (cancelled, failed, or still downloading). Currently ignored; decide whether they warrant their own report.
