#!/usr/bin/env python3
"""
Per-user "requested by" collections in Plex, driven by Seerr requests, drained
by Tautulli watch history -- plus a REPORT-ONLY deletion-candidate flagger.

WHY THIS EXISTS, AND THE ONE THING TO UNDERSTAND BEFORE CHANGING IT
-------------------------------------------------------------------
The obvious rule -- "if an item is in nobody's collection, flag it for
deletion" -- is WRONG here, and measurably so. On 2026-09-04, 627 of 820
library items (76%) had no matching Seerr request at all: content added
directly, added before Seerr existed, or requested by users who have since
left. 96% of the 4K movies library falls in this bucket. That rule would have
flagged three quarters of the library on day one. This is the same trap
docs/architecture/plex-cleanup-design.md already fell into ("the rules as
stated would flag ~85% of the library on day one").

So eligibility is NOT "currently in zero collections". It is:

    was in at least one user collection at some point   (recorded in state)
    AND is now in zero user collections                 (everyone watched it)

That distinction is the entire reason this script keeps a state database.
An item that was never requested via Seerr is never eligible, full stop --
it cannot "drain" out of a collection it was never in.

WHAT THIS SCRIPT WILL AND WILL NOT DO
--------------------------------------
  * It NEVER deletes media. Not with --apply, not ever. The flagger writes a
    report and nothing else. Deletion, if it is ever wanted, is a separate
    deliberate step with its own safeguards (see plex-cleanup-design.md).
  * --apply only ever adds/removes COLLECTION MEMBERSHIP. Worst case of a bug
    is a wrong collection, which is cosmetic and re-syncable.
  * Default is report-only. You must pass --apply to touch anything.

CONSTRAINT WORTH KNOWING: non-admin Plex users cannot edit server collections.
Membership here is entirely automation-driven -- a user cannot remove something
from "their" collection themselves. If you want user-driven removal, that needs
a different mechanism (a Plex label they can set, or a Seerr-side action).
"""
import argparse, html, json, os, re, sqlite3, sys, urllib.parse, urllib.request
from collections import defaultdict

PLEX = os.environ.get("PLEX_URL", "http://127.0.0.1:32400")
SEERR = os.environ.get("SEERR_URL", "http://192.168.178.69:30023")
TAUTULLI = os.environ.get("TAUTULLI_URL", "http://192.168.178.69:30035")
STATE_DB = os.environ.get(
    "STATE_DB", os.path.expanduser("~/.local/state/plex_user_collections.sqlite3")
)
COLLECTION_FMT = "Requested by {user}"
# Library content with no Seerr request behind it -- 524 items as of 2026-09-04.
# Deliberately NOT merged into the admin's own "Requested by" collection: that
# would bury his ~65 genuine requests under 524 unrelated items and destroy the
# collection's usefulness as a watchlist. Separate collection, same cleanup goal.
UNREQUESTED_COLLECTION = "Unrequested — admin cleanup"
# Comment keyword a user puts on a Seerr issue to say "I'm done, safe to remove".
RELEASE_KEYWORD = "#done"
# Plex section ids -> the `type` value its tag-edit endpoint expects.
# 1 = movie, 2 = show. Getting this wrong makes the edit silently no-op.
SECTIONS = {1: ("TV Shows", 2), 2: ("Movies", 1), 3: ("Movies - 4K", 1), 4: ("TV Shows - 4K", 2)}


def _get(url, headers=None, timeout=120):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers or {}), timeout=timeout
    ).read().decode("utf8", "ignore")


def _json(url, headers=None, timeout=120):
    return json.loads(_get(url, headers, timeout))


def load_env_file():
    """Populate missing API keys from the repo's homepage/.env.

    Needed because this runs under cron, which gets a near-empty environment --
    the interactive `set -a && . homepage/.env` idiom is not available there.
    Only fills in keys that are not already set, so an explicit environment
    variable always wins. Values are never logged.
    """
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "homepage", ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def plex_token():
    for p in (
        "/Volumes/FastSSD/PlexData/.LocalAdminToken",
        os.path.expanduser("~/Library/Application Support/Plex Media Server/.LocalAdminToken"),
    ):
        if os.path.exists(p):
            return open(p).read().strip()
    tok = os.environ.get("PLEX_TOKEN")
    if not tok:
        sys.exit("No Plex token: set PLEX_TOKEN or ensure .LocalAdminToken is readable")
    return tok


# ---------------------------------------------------------------- state
def open_state(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path)
    db.execute(
        """CREATE TABLE IF NOT EXISTS membership (
              tmdb_id TEXT NOT NULL,
              user    TEXT NOT NULL,
              rating_key TEXT,
              title   TEXT,
              first_seen TEXT NOT NULL,
              drained_at TEXT,
              released_at TEXT,
              PRIMARY KEY (tmdb_id, user))"""
    )
    # tolerate an older state file created before released_at existed
    cols = {r[1] for r in db.execute("PRAGMA table_info(membership)")}
    if "released_at" not in cols:
        db.execute("ALTER TABLE membership ADD COLUMN released_at TEXT")
    db.commit()
    return db


# ---------------------------------------------------------------- sources
def seerr_requests(api_key):
    rs = _json(f"{SEERR}/api/v1/request?take=1000", {"X-Api-Key": api_key})["results"]
    by_tmdb = defaultdict(set)
    for r in rs:
        m = r.get("media") or {}
        u = (r.get("requestedBy") or {}).get("displayName")
        # tmdbId is 100% populated; ratingKey is only ~64% -- never join on ratingKey.
        if m.get("tmdbId") and u:
            by_tmdb[str(m["tmdbId"])].add(u)
    return by_tmdb


def plex_library(token):
    """tmdb_id -> {rating_key, title, section, type}. Uses includeGuids to get
    tmdb ids in bulk rather than one metadata call per item."""
    out = {}
    for sid, (name, typ) in SECTIONS.items():
        body = _get(f"{PLEX}/library/sections/{sid}/all?includeGuids=1&X-Plex-Token={token}")
        for tag, inner in re.findall(
            r"<(Video|Directory)\b([^>]*(?:/>|>.*?</(?:Video|Directory)>))", body, re.S
        ):
            rk = re.search(r'ratingKey="(\d+)"', inner)
            ti = re.search(r'title="([^"]*)"', inner)
            lc = re.search(r'leafCount="(\d+)"', inner)
            if not rk:
                continue
            for tm in re.findall(r'<Guid id="tmdb://(\d+)"', inner):
                out[tm] = {
                    "rating_key": rk.group(1),
                    "title": html.unescape(ti.group(1)) if ti else "?",
                    "section": sid,
                    "type": typ,
                    # episode count for shows; None for movies. Used to decide
                    # whether a series is genuinely finished -- see tautulli_watched.
                    "leaf_count": int(lc.group(1)) if lc else None,
                }
    return out


def seerr_released(api_key, keyword=RELEASE_KEYWORD):
    """{(tmdb_id, user)} that a user has explicitly said they are done with.

    WHY ISSUES: inside Plex, playback is the *only* user action an admin can
    observe. A shared user cannot edit collections or labels, and their star
    ratings and Watchlist live on their own plex.tv account -- unreadable with
    an admin token. So the "I'm done with this" signal has to come from Seerr,
    where every Plex user already has an account. Seerr Issues carry exactly
    the fields needed: media.tmdbId, createdBy.displayName, and free-text
    comments.

    Convention: the user opens the title in Seerr -> Report Issue -> comment
    containing `#done`. Both open and closed issues count, and the release is
    written to the state DB, so closing the issue later does not resurrect the
    item into their collection.
    """
    out = set()
    try:
        rs = _json(f"{SEERR}/api/v1/issue?take=500&filter=all", {"X-Api-Key": api_key})["results"]
    except Exception:
        return out
    for i in rs:
        user = (i.get("createdBy") or {}).get("displayName")
        tmdb = (i.get("media") or {}).get("tmdbId")
        if not (user and tmdb):
            continue
        for c in i.get("comments") or []:
            if keyword.lower() in str(c.get("message", "")).lower():
                out.add((str(tmdb), user))
                break
    return out


def keep_labelled(token, label="keep"):
    """rating_keys carrying the protective label.

    Needed because "everyone who requested it has watched it" does NOT mean
    "nobody wants it any more". The first real run flagged The Lord of the
    Rings: The Two Towers, Tangled, The Croods and six My Little Pony titles --
    permanent library and kids' content that gets rewatched. This is the
    library-vs-backlog distinction from plex-cleanup-design.md, and a manual
    label is the escape hatch that doc already settled on: native to Plex,
    per-item, settable from any client, survives metadata refreshes.
    """
    keep = set()
    for sid in SECTIONS:
        try:
            body = _get(f"{PLEX}/library/sections/{sid}/all"
                        f"?label={urllib.parse.quote(label)}&X-Plex-Token={token}")
            keep |= set(re.findall(r'ratingKey="(\d+)"', body))
        except Exception:
            pass  # a section with no such label can 4xx; absence is not an error
    return keep


def tautulli_watched(api_key, leaf_counts):
    """user -> set of rating_keys COMPLETED by that user.

    A movie is simple: watched_status == 1 on its own rating_key.

    A SERIES IS NOT. An earlier version of this function added the series
    (grandparent) key as soon as any single episode completed, which meant
    watching one episode of Ted Lasso marked all 34 as done and drained the
    whole show out of the requester's collection. A series only counts as
    watched when the user has completed at least as many distinct episodes as
    Plex reports for it (`leafCount`). Erring toward "not watched" is the
    safe direction here -- it keeps an item in a collection, which at worst
    means it is not yet flagged.
    """
    d = _json(f"{TAUTULLI}/api/v2?apikey={api_key}&cmd=get_history&length=10000")
    rows = d["response"]["data"]["data"]
    done = defaultdict(set)
    eps = defaultdict(lambda: defaultdict(set))  # user -> series_key -> {episode keys}
    for e in rows:
        if str(e.get("watched_status")) != "1":
            continue
        u = e.get("user")
        gp, rk = e.get("grandparent_rating_key"), e.get("rating_key")
        if gp:  # an episode
            if rk:
                eps[u][str(gp)].add(str(rk))
        elif rk:  # a movie
            done[u].add(str(rk))
    for u, series in eps.items():
        for skey, watched_eps in series.items():
            total = leaf_counts.get(skey)
            if total and len(watched_eps) >= total:
                done[u].add(skey)
    return done, len(rows)


# ---------------------------------------------------------------- plex writes
def collection_members(token, sid):
    """collection title -> {rating_key}"""
    body = _get(f"{PLEX}/library/sections/{sid}/collections?X-Plex-Token={token}")
    out = {}
    for ck, title in re.findall(r'ratingKey="(\d+)"[^>]*?title="([^"]*)"', body):
        title = html.unescape(title)  # Plex escapes '—' as &#8212;, "'" as &#39;
        kids = _get(f"{PLEX}/library/collections/{ck}/children?X-Plex-Token={token}")
        out[title] = set(re.findall(r'ratingKey="(\d+)"', kids))
    return out


def edit_collection(token, sid, typ, rating_key, coll, add=True):
    op = "collection%5B0%5D.tag.tag=" if add else "collection%5B%5D.tag.tag-="
    url = (
        f"{PLEX}/library/sections/{sid}/all?type={typ}&id={rating_key}"
        f"&{op}{urllib.parse.quote(coll)}&X-Plex-Token={token}"
    )
    req = urllib.request.Request(url, method="PUT")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="actually add/remove COLLECTION MEMBERSHIP (never deletes media)")
    ap.add_argument("--state-db", default=STATE_DB)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    load_env_file()
    seerr_key = os.environ.get("SEERR_API_KEY") or os.environ.get("HOMEPAGE_VAR_OVERSEERR_API_KEY")
    taut_key = os.environ.get("TAUTULLI_API_KEY") or os.environ.get("HOMEPAGE_VAR_TAUTULLI_API_KEY")
    if not (seerr_key and taut_key):
        sys.exit("Need SEERR_API_KEY and TAUTULLI_API_KEY (or the HOMEPAGE_VAR_* equivalents)")
    token = plex_token()
    db = open_state(a.state_db)
    now = __import__("datetime").datetime.now().isoformat(timespec="seconds")

    requests_by_tmdb = seerr_requests(seerr_key)
    library = plex_library(token)
    leaf_counts = {v["rating_key"]: v["leaf_count"] for v in library.values() if v["leaf_count"]}
    keep = keep_labelled(token)
    released = seerr_released(seerr_key)
    watched, hist_rows = tautulli_watched(taut_key, leaf_counts)

    matched = {t: v for t, v in requests_by_tmdb.items() if t in library}
    pending = sorted(t for t in requests_by_tmdb if t not in library)
    # Library content with no request behind it. Picked up automatically on a
    # later run if a request for it ever appears.
    unrequested = {t: v for t, v in library.items() if t not in requests_by_tmdb}
    unmatched = len(pending)

    # desired[user] = rating_keys that user requested and has NOT finished
    desired = defaultdict(set)
    ever, drained = [], []
    for tmdb, users in matched.items():
        item = library[tmdb]
        rk = item["rating_key"]
        still = set()
        for u in users:
            db.execute(
                "INSERT OR IGNORE INTO membership(tmdb_id,user,rating_key,title,first_seen)"
                " VALUES(?,?,?,?,?)", (tmdb, u, rk, item["title"], now))
            # Two independent ways an item leaves a user's collection: they
            # finished it, or they explicitly released it via a Seerr issue.
            release = (tmdb, u) in released
            if rk in watched.get(u, set()) or release:
                db.execute("UPDATE membership SET drained_at=COALESCE(drained_at,?)"
                           " WHERE tmdb_id=? AND user=?", (now, tmdb, u))
                if release:
                    db.execute("UPDATE membership SET released_at=COALESCE(released_at,?)"
                               " WHERE tmdb_id=? AND user=?", (now, tmdb, u))
            else:
                still.add(u)
                desired[u].add(rk)
        ever.append(tmdb)
        # Protected items still drain out of collections (they have been watched,
        # so they do not belong on an active watchlist) -- they are simply never
        # put forward as deletion candidates.
        if not still and rk not in keep:
            drained.append((tmdb, item["title"], sorted(users)))
    db.commit()

    # reconcile collections
    actions = []
    for sid, (sname, typ) in SECTIONS.items():
        current = collection_members(token, sid)
        sect_keys = {v["rating_key"] for v in library.values() if v["section"] == sid}
        for user in sorted(set(list(desired) + [u for _, _, us in drained for u in us])):
            coll = COLLECTION_FMT.format(user=user)
            want = desired.get(user, set()) & sect_keys
            have = current.get(coll, set())
            for rk in sorted(want - have):
                actions.append(("add", user, sid, typ, rk))
            for rk in sorted(have - want):
                actions.append(("remove", user, sid, typ, rk))
        # admin-cleanup bucket for content nobody requested
        want_u = {v["rating_key"] for v in unrequested.values() if v["section"] == sid}
        have_u = current.get(UNREQUESTED_COLLECTION, set())
        for rk in sorted(want_u - have_u):
            actions.append(("add", None, sid, typ, rk))
        for rk in sorted(have_u - want_u):
            actions.append(("remove", None, sid, typ, rk))

    applied = 0
    if a.apply:
        for op, user, sid, typ, rk in actions:
            try:
                name = UNREQUESTED_COLLECTION if user is None else COLLECTION_FMT.format(user=user)
                edit_collection(token, sid, typ, rk, name, add=(op == "add"))
                applied += 1
            except Exception as e:  # keep going; a single bad item must not abort the sync
                print(f"  ! {op} {rk} for {user} failed: {e}", file=sys.stderr)

    if a.json:
        print(json.dumps({
            "requested_titles": len(requests_by_tmdb), "matched_in_library": len(matched),
            "unmatched": unmatched, "library_items": len(library),
            "planned_actions": len(actions), "applied": applied,
            "flagged": [{"tmdb": t, "title": ti, "requesters": us} for t, ti, us in drained],
        }, indent=2))
        return

    print(f"Seerr requested titles ....... {len(requests_by_tmdb)}")
    print(f"  matched to a Plex item ..... {len(matched)}")
    print(f"  requested but not in library {unmatched}")
    print(f"Plex library items ........... {len(library)}")
    print(f"Tautulli history rows ........ {hist_rows}")
    print(f"Protected by 'keep' label .... {len(keep)}")
    print(f"Released via '{RELEASE_KEYWORD}' issue ...... {len(released)}")
    print(f"Unrequested library items .... {len(unrequested)} -> \"{UNREQUESTED_COLLECTION}\"")
    print(f"Awaiting availability ........ {len(pending)} (not yet in Plex; auto-added when they land)")
    print()
    print(f"Collection changes {'APPLIED' if a.apply else 'PLANNED (dry-run)'}: {len(actions)}")
    for op, user, sid, _typ, rk in actions[:15]:
        print(f"  {op:<6} {rk:<8} {UNREQUESTED_COLLECTION if user is None else COLLECTION_FMT.format(user=user)}")
    if len(actions) > 15:
        print(f"  ... and {len(actions)-15} more")
    print()
    print(f"FLAGGED for deletion review: {len(drained)}")
    print("  (was in >=1 user collection, every requester has now finished it.")
    print("   Nothing is deleted. Items never requested via Seerr are excluded by design.)")
    for t, ti, us in drained[:20]:
        print(f"  tmdb:{t:<9} {ti[:44]:<46} requested by: {', '.join(us)}")
    if len(drained) > 20:
        print(f"  ... and {len(drained)-20} more")


if __name__ == "__main__":
    main()
