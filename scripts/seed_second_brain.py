#!/usr/bin/env python3
"""
Bulk-load facts into the second brain's Qdrant memory.

Usage:
    python3 scripts/seed_second_brain.py <file-or-directory> [more paths...]

Accepts .md or .txt files. Each file is split into chunks on blank lines
(paragraph-level) so retrieval later can point back to specific facts
rather than whole documents. Each chunk gets embedded via Ollama
(nomic-embed-text) and upserted into Qdrant's `second_brain` collection.

Safe to re-run, including on edited files: before (re-)inserting a file's
chunks, every existing point tagged with that exact file path as its
`source` is deleted first, so stale/removed content never lingers. Only
touches points from that source path — Discord-originated memory (facts,
conversations, photos, journal entries) is untouched, since those use a
different payload shape entirely.
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/embeddings"
QDRANT_URL = "http://localhost:6333/collections/second_brain/points"
EMBED_MODEL = "nomic-embed-text"


MAX_WORDS_PER_CHUNK = 700  # ~2048 tokens is the embedding model's hard limit; stay well under it


def _split_oversized(chunk: str) -> list[str]:
    """A paragraph with no blank lines (long bullet, big markdown table) can
    still blow past the embedding model's context window. Fall back to
    grouping individual lines up to a safe word count."""
    words = chunk.split()
    if len(words) <= MAX_WORDS_PER_CHUNK:
        return [chunk]
    lines = chunk.split("\n")
    if len(lines) > 1:
        pieces, current, current_words = [], [], 0
        for line in lines:
            w = len(line.split())
            if current and current_words + w > MAX_WORDS_PER_CHUNK:
                pieces.append("\n".join(current))
                current, current_words = [], 0
            current.append(line)
            current_words += w
        if current:
            pieces.append("\n".join(current))
        return [p for p in pieces if p.strip()]
    # single unbroken line longer than the limit - hard-split on words
    return [" ".join(words[i:i + MAX_WORDS_PER_CHUNK]) for i in range(0, len(words), MAX_WORDS_PER_CHUNK)]


def chunk_text(text: str) -> list[str]:
    chunks = [c.strip() for c in text.split("\n\n")]
    chunks = [c for c in chunks if len(c) > 20]  # skip trivial fragments
    out = []
    for c in chunks:
        out.extend(_split_oversized(c))
    return out


def embed(text: str) -> list[float]:
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({"model": EMBED_MODEL, "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embedding"]


def upsert(point_id: int, vector: list[float], text: str, source: str):
    req = urllib.request.Request(
        QDRANT_URL,
        method="PUT",
        data=json.dumps(
            {
                "points": [
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": {"text": text, "source": source},
                    }
                ]
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        json.load(resp)


def point_id_for(source: str, text: str) -> int:
    h = hashlib.sha256(f"{source}:{text}".encode()).hexdigest()
    return int(h[:15], 16)  # fits comfortably in a 64-bit int, Qdrant accepts ints


def delete_by_source(source: str):
    req = urllib.request.Request(
        f"{QDRANT_URL}/delete",
        method="POST",
        data=json.dumps(
            {"filter": {"must": [{"key": "source", "match": {"value": source}}]}}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        json.load(resp)


def process_file(path: Path) -> int:
    text = path.read_text(errors="ignore")
    chunks = chunk_text(text)
    delete_by_source(str(path))
    for chunk in chunks:
        vector = embed(chunk)
        upsert(point_id_for(str(path), chunk), vector, chunk, str(path))
    return len(chunks)


def main(paths: list[str]):
    if not paths:
        print(__doc__)
        sys.exit(1)

    total = 0
    for raw in paths:
        p = Path(raw).expanduser()
        files = (
            [f for f in p.rglob("*") if f.suffix in (".md", ".txt")]
            if p.is_dir()
            else [p]
        )
        for f in files:
            n = process_file(f)
            print(f"  {f}: {n} chunks")
            total += n

    print(f"Done — {total} chunks stored in Qdrant's second_brain collection.")


if __name__ == "__main__":
    main(sys.argv[1:])
