#!/usr/bin/env python3
"""
Export everything the second brain knows to a readable markdown file.

Usage:
    python3 scripts/export_second_brain.py [output-path]

Defaults to writing brain_export_<date>.md in the current directory.
Read-only — never modifies Qdrant. Paginates through the entire
collection (not just a sample), grouping points by their `type` payload
field (fact, conversation, photo, journal, apple_health, or untyped —
mostly the seeded docs/ content, which has no `type`, only `source`).
"""
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import date

QDRANT_URL = "http://localhost:6333/collections/second_brain/points/scroll"


def fetch_all_points():
    points = []
    offset = None
    while True:
        body = {"limit": 200, "with_payload": True, "with_vector": False}
        if offset is not None:
            body["offset"] = offset
        req = urllib.request.Request(
            QDRANT_URL,
            method="POST",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)["result"]
        points.extend(data["points"])
        offset = data.get("next_page_offset")
        if offset is None:
            break
    return points


def main(out_path: str):
    points = fetch_all_points()
    groups = defaultdict(list)
    for p in points:
        payload = p.get("payload", {})
        kind = payload.get("type") or ("doc" if payload.get("source") else "other")
        groups[kind].append(payload)

    lines = [f"# Second Brain Export — {date.today().isoformat()}", "", f"Total points: {len(points)}", ""]

    order = ["fact", "journal", "photo", "apple_health", "conversation", "doc", "other"]
    titles = {
        "fact": "Facts", "journal": "Journal Entries", "photo": "Photos",
        "apple_health": "Apple Health Workouts", "conversation": "Conversation Log",
        "doc": "Seeded Documentation", "other": "Uncategorized",
    }
    for kind in order:
        items = groups.get(kind, [])
        if not items:
            continue
        lines.append(f"## {titles.get(kind, kind)} ({len(items)})")
        lines.append("")
        for item in items:
            date_str = f"[{item['date']}] " if item.get("date") else ""
            tag_str = f" `{item['domain']}:{','.join(item.get('tags') or [])}`" if item.get("domain") else ""
            lines.append(f"- {date_str}{item.get('text', '(no text)')}{tag_str}")
        lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Exported {len(points)} points to {out_path}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else f"brain_export_{date.today().isoformat()}.md"
    main(out)
