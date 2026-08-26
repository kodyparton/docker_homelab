#!/usr/bin/env python3
"""
Read-only report of what a Plex "Leaving Soon" cleanup WOULD flag.
Makes no changes to Plex, Radarr, Sonarr, or Overseerr - it only reads.

This is the evaluation half of the design in
docs/architecture/plex-cleanup-design.md. Deliberately kept separate from
anything that deletes, so the rules can be tuned against real data first.

Usage:
    python3 scripts/plex_cleanup_candidates.py                    # summary to stdout
    python3 scripts/plex_cleanup_candidates.py --csv out.csv      # + full CSV
    python3 scripts/plex_cleanup_candidates.py --days 180         # different threshold

Rules implemented (matching the design doc):
  - "Stale" = no view in --days (default 365).
  - Items never viewed fall back to their added-at date, but are reported
    in their own category, since whether those should ever be deleted is
    an open decision.
  - 4K and 1080p copies of the same title are treated as ONE title: a view
    of either counts as a view of both. Plex tracks them separately, so
    without this a naive run would delete the copy you don't happen to use.
  - Shows that are part-watched (some but not all episodes) are reported
    separately - deleting mid-watch is the worst outcome.
  - Anything carrying the `keep` Plex label is excluded outright.
"""
import argparse
import csv
import datetime
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from infisical_client import get_secret

PLEX = "http://localhost:32400"
SECTIONS = {"1": "TV Shows", "2": "Movies", "3": "Movies - 4K", "4": "TV Shows - 4K"}
KEEP_LABEL = "keep"
DAY = 86400


def plex_get(path, token, **params):
    params["X-Plex-Token"] = token
    url = f"{PLEX}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["MediaContainer"]


def norm_title(item):
    """Key for matching the same title across the 4K and standard libraries."""
    return (item.get("title", "").strip().lower(), item.get("year"))


def has_keep_label(item):
    return any(l.get("tag", "").lower() == KEEP_LABEL for l in item.get("Label", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365, help="staleness threshold (default 365)")
    ap.add_argument("--csv", help="write full candidate list to this CSV path")
    args = ap.parse_args()

    token = get_secret("PLEX_TOKEN")
    now = datetime.datetime.now().timestamp()
    cutoff = args.days * DAY

    # Pull every item from every section.
    all_items = []
    for sid, sname in SECTIONS.items():
        data = plex_get(f"/library/sections/{sid}/all", token, includeLabels=1)
        for it in data.get("Metadata", []):
            it["_section"] = sname
            it["_section_id"] = sid
            all_items.append(it)

    # Cross-library view reconciliation: a view of ANY copy counts for all copies.
    best_view = {}
    for it in all_items:
        k = norm_title(it)
        lv = it.get("lastViewedAt")
        if lv and lv > best_view.get(k, 0):
            best_view[k] = lv

    rows = []
    for it in all_items:
        k = norm_title(it)
        effective_view = best_view.get(k) or it.get("lastViewedAt")
        own_view = it.get("lastViewedAt")
        added = it.get("addedAt")
        # reference date: last view of any copy, else when it was added
        ref = effective_view or added
        if not ref:
            continue
        age_days = int((now - ref) / DAY)
        if age_days <= args.days:
            continue

        if has_keep_label(it):
            category = "protected (keep label)"
        elif not effective_view:
            category = "never watched"
        elif it.get("type") == "show" and 0 < (it.get("viewedLeafCount") or 0) < (it.get("leafCount") or 0):
            category = "part-watched show"
        else:
            category = "watched, gone cold"

        dup = len([x for x in all_items if norm_title(x) == k]) > 1

        rows.append({
            "category": category,
            "section": it["_section"],
            "title": it.get("title", ""),
            "year": it.get("year", ""),
            "days_since": age_days,
            "last_viewed": datetime.datetime.fromtimestamp(effective_view).strftime("%Y-%m-%d") if effective_view else "never",
            "viewed_other_copy_only": "yes" if (effective_view and not own_view) else "",
            "added": datetime.datetime.fromtimestamp(added).strftime("%Y-%m-%d") if added else "",
            "episodes": it.get("leafCount", ""),
            "episodes_watched": it.get("viewedLeafCount", ""),
            "has_4k_or_hd_duplicate": "yes" if dup else "",
            "rating_key": it.get("ratingKey", ""),
        })

    rows.sort(key=lambda r: -r["days_since"])

    total_by_section = {}
    for it in all_items:
        total_by_section[it["_section"]] = total_by_section.get(it["_section"], 0) + 1

    print(f"Plex cleanup candidates - threshold {args.days} days ({args.days // 365}y)")
    print(f"Read-only report. Nothing was modified.\n")

    print("BY SECTION")
    for sname in SECTIONS.values():
        flagged = sum(1 for r in rows if r["section"] == sname and not r["category"].startswith("protected"))
        total = total_by_section.get(sname, 0)
        pct = (flagged / total * 100) if total else 0
        print(f"  {sname:16} {flagged:4} of {total:4} flagged ({pct:.0f}%)")

    print("\nBY CATEGORY")
    for cat in ["watched, gone cold", "never watched", "part-watched show", "protected (keep label)"]:
        n = sum(1 for r in rows if r["category"] == cat)
        print(f"  {cat:26} {n:4}")

    dupes = sum(1 for r in rows if r["has_4k_or_hd_duplicate"])
    saved = sum(1 for r in rows if r["viewed_other_copy_only"])
    print(f"\n  flagged items that exist in both 4K and HD: {dupes}")
    print(f"  ...of which were SAVED from wrong deletion by cross-library matching: {saved}")

    print("\nOLDEST 15 CANDIDATES")
    for r in rows[:15]:
        print(f"  {r['days_since']:5}d  {r['title'][:38]:40} {r['section']:14} [{r['category']}]")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nFull list ({len(rows)} rows) written to {args.csv}")


if __name__ == "__main__":
    main()
