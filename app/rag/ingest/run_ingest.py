"""Refresh the corpus from live IL sources (SPEC §3).

    python -m app.rag.ingest.run_ingest            # refresh all sources
    python -m app.rag.ingest.run_ingest --dry-run  # show what would be fetched

Writes refreshed snapshots into data/corpus/_fetched/ (gitignored) so a refresh
never clobbers the curated, human-checked seed snapshots. Review a refreshed file
and copy it over the seed when you've verified it.

Runs fully offline-safe: if the network is unavailable, it reports the failure
per source and exits without corrupting anything.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.rag.ingest.clean import chunk_text, html_to_text
from app.rag.ingest.sources import SOURCES, Source


def _fetch(url: str, timeout: float = 20.0) -> Optional[str]:
    try:
        import httpx

        headers = {"User-Agent": "ParaPilot-ingest/0.1 (+legal-information tool)"}
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:  # network/HTTP errors are expected offline
        print("  ! fetch failed: {}".format(exc), file=sys.stderr)
        return None


def ingest_source(src: Source, out_dir: Path, dry_run: bool = False) -> bool:
    print("- {} <{}>".format(src.source_id, src.url))
    if dry_run:
        return True

    html = _fetch(src.url)
    if html is None:
        return False

    text = html_to_text(html)
    pieces = chunk_text(text)
    if not pieces:
        print("  ! no usable text extracted", file=sys.stderr)
        return False

    doc = {
        "source_id": src.source_id,
        "title": src.title,
        "url": src.url,
        "publisher": src.publisher,
        "jurisdiction": src.jurisdiction,
        "topic": src.topic,
        "retrieved": date.today().isoformat(),
        "license_note": "Auto-ingested snapshot. REVIEW before promoting over the curated seed.",
        "chunks": [
            {"id": "{}_{:03d}".format(src.source_id, i), "heading": "", "text": piece, "tags": []}
            for i, piece in enumerate(pieces)
        ],
    }
    out_path = out_dir / "{}.json".format(src.source_id)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  -> wrote {} chunks to {}".format(len(pieces), out_path))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh ParaPilot corpus from live sources.")
    parser.add_argument("--dry-run", action="store_true", help="List sources without fetching.")
    args = parser.parse_args()

    settings = get_settings()
    out_dir = settings.corpus_path / "_fetched"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Ingesting {} sources -> {}".format(len(SOURCES), out_dir))
    ok = 0
    for src in SOURCES:
        if ingest_source(src, out_dir, dry_run=args.dry_run):
            ok += 1

    print("\nDone: {}/{} sources processed.".format(ok, len(SOURCES)))
    if ok == 0 and not args.dry_run:
        print(
            "No sources fetched (likely offline). The bundled seed corpus in "
            "data/corpus/*.json is unchanged and the app still works offline.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
