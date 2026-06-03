"""Turn inline [n] markers in an answer into Citation objects.

We only emit citations for markers the model actually used AND that map to a real
retrieved chunk. Markers that point past the context are dropped (defensive
against a model inventing [9] when only 4 passages exist).
"""
from __future__ import annotations

import re
from typing import List

from app.schemas import Citation, RetrievedChunk

_MARKER_RE = re.compile(r"\[(\d+)\]")


def _snippet(text: str, limit: int = 320) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def used_marker_indices(answer: str) -> List[int]:
    """Distinct 1-based marker numbers used in the answer, in first-seen order."""
    seen = []
    for m in _MARKER_RE.finditer(answer):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def build_citations(answer: str, context: List[RetrievedChunk]) -> List[Citation]:
    """Map used [n] markers to Citation objects (n is 1-based into context)."""
    citations: List[Citation] = []
    for n in used_marker_indices(answer):
        if 1 <= n <= len(context):
            c = context[n - 1]
            citations.append(
                Citation(
                    marker=str(n),
                    source_id=c.source_id,
                    chunk_id=c.chunk_id,
                    title=c.title,
                    url=c.url,
                    publisher=c.publisher,
                    retrieved=c.retrieved,
                    snippet=_snippet(c.text),
                )
            )
    return citations


def strip_unsupported_markers(answer: str, context_len: int) -> str:
    """Remove any [n] where n is out of range, so the UI never shows a dead cite."""

    def repl(m: "re.Match") -> str:
        n = int(m.group(1))
        return m.group(0) if 1 <= n <= context_len else ""

    cleaned = _MARKER_RE.sub(repl, answer)
    # Collapse any double spaces left behind by a removed marker.
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()
