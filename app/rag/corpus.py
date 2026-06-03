"""Load the bundled offline seed corpus.

The corpus is a set of JSON files in ``data/corpus/`` (one per source). Each
file has source metadata + a list of chunks. We flatten them into
``RetrievedChunk``-shaped records (score filled in by the retriever).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from app.config import get_settings


class Chunk:
    """A single retrievable unit of grounded text plus its provenance."""

    __slots__ = (
        "source_id", "chunk_id", "title", "url", "publisher",
        "retrieved", "heading", "text", "tags",
    )

    def __init__(
        self,
        source_id: str,
        chunk_id: str,
        title: str,
        url: str,
        publisher: str,
        retrieved: str,
        heading: str,
        text: str,
        tags: List[str],
    ) -> None:
        self.source_id = source_id
        self.chunk_id = chunk_id
        self.title = title
        self.url = url
        self.publisher = publisher
        self.retrieved = retrieved
        self.heading = heading
        self.text = text
        self.tags = tags

    @property
    def key(self) -> str:
        return self.source_id + "::" + self.chunk_id

    @property
    def search_text(self) -> str:
        """Text used for lexical/embedding matching (heading + tags + body)."""
        return " ".join([self.heading, " ".join(self.tags), self.text])


def load_corpus(corpus_dir: Path = None) -> List[Chunk]:
    """Read every ``*.json`` source file and return a flat list of chunks."""
    settings = get_settings()
    base = corpus_dir or settings.corpus_path
    chunks: List[Chunk] = []

    if not base.exists():
        return chunks

    for path in sorted(base.glob("*.json")):
        if path.name.startswith("_"):
            continue
        with path.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)

        # Per-source defaults; a chunk may override url for granular linking.
        s_url = doc.get("url", "")
        for ch in doc.get("chunks", []):
            chunks.append(
                Chunk(
                    source_id=doc["source_id"],
                    chunk_id=ch["id"],
                    title=doc.get("title", doc["source_id"]),
                    url=ch.get("url", s_url),
                    publisher=doc.get("publisher", ""),
                    retrieved=doc.get("retrieved", ""),
                    heading=ch.get("heading", ""),
                    text=ch["text"],
                    tags=ch.get("tags", []),
                )
            )
    return chunks


def corpus_stats(corpus_dir: Path = None) -> Dict[str, int]:
    chunks = load_corpus(corpus_dir)
    sources = {c.source_id for c in chunks}
    return {"sources": len(sources), "chunks": len(chunks)}
