"""Tests for hybrid retrieval and the corpus loader."""
from __future__ import annotations

from app.rag.corpus import corpus_stats, load_corpus
from app.rag.retriever import Retriever


def test_corpus_loads():
    chunks = load_corpus()
    assert len(chunks) > 20
    # Every chunk has provenance.
    for c in chunks:
        assert c.source_id and c.chunk_id and c.text
        assert c.url.startswith("http")


def test_corpus_stats():
    stats = corpus_stats()
    assert stats["sources"] >= 5
    assert stats["chunks"] >= 20


def test_retrieval_finds_relevant_chunk(retriever):
    hits = retriever.search("residency requirement to file for divorce", top_k=4)
    assert hits
    joined = " ".join(h.text for h in hits).lower()
    assert "90 days" in joined


def test_retrieval_publication(retriever):
    hits = retriever.search("cannot locate my spouse to serve", top_k=4)
    assert any("publication" in h.text.lower() for h in hits)


def test_retrieval_scores_descending(retriever):
    hits = retriever.search("parenting plan children", top_k=5)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_confidence_zero_for_no_hits(retriever):
    hits = retriever.search("zzzqqq nonsense token xyzzy", top_k=4)
    assert Retriever.confidence(hits) == 0.0


def test_confidence_high_for_strong_match(retriever):
    hits = retriever.search("how do I get a fee waiver", top_k=4)
    assert Retriever.confidence(hits) > 0.3
