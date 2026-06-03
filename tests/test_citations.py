"""Tests for citation parsing and dead-marker stripping."""
from __future__ import annotations

from app.rag.citations import (
    build_citations,
    strip_unsupported_markers,
    used_marker_indices,
)
from app.schemas import RetrievedChunk


def _chunks(n):
    return [
        RetrievedChunk(
            source_id="s%d" % i,
            chunk_id="c%d" % i,
            title="T%d" % i,
            url="https://example.com/%d" % i,
            publisher="Pub%d" % i,
            retrieved="2026-06-03",
            heading="H%d" % i,
            text="Body text number %d." % i,
            score=1.0 - 0.1 * i,
        )
        for i in range(1, n + 1)
    ]


def test_used_marker_indices_dedup_and_order():
    assert used_marker_indices("Foo [2] bar [1] baz [2]") == [2, 1]


def test_build_citations_maps_markers():
    ctx = _chunks(3)
    cites = build_citations("A [1] B [3]", ctx)
    assert [c.marker for c in cites] == ["1", "3"]
    assert cites[0].source_id == "s1"
    assert cites[1].chunk_id == "c3"


def test_build_citations_ignores_out_of_range():
    ctx = _chunks(2)
    cites = build_citations("A [1] B [9]", ctx)
    assert [c.marker for c in cites] == ["1"]


def test_strip_unsupported_markers():
    out = strip_unsupported_markers("Claim one [1] and claim two [9].", context_len=2)
    assert "[9]" not in out
    assert "[1]" in out


def test_strip_collapses_extra_spaces():
    out = strip_unsupported_markers("A  [5]  B", context_len=1)
    assert "  " not in out
