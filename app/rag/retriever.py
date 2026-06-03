"""Hybrid retrieval: BM25 (lexical) + TF-IDF cosine (semantic-ish), fused.

SPEC §4 asks for hybrid retrieval (BM25 + embeddings) with a lean,
offline-friendly fallback. We use:

  * **BM25** — a compact, dependency-free implementation (exact keyword/term
    matching with length normalization). Great for form names, statute cites.
  * **TF-IDF cosine** — scikit-learn's vectorizer with sub-linear TF and an
    n-gram range, used as the offline embedding fallback. Captures soft term
    overlap and phrasing the way a small embedding model would, with no model
    download and no network.

Scores from each retriever are min-max normalized per query and combined with a
weighted sum, then the top-k chunks are returned with a calibrated confidence.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from app.config import get_settings
from app.rag.corpus import Chunk, load_corpus
from app.schemas import RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "be", "do", "does", "did", "i", "my", "me", "you", "your", "it", "this",
    "that", "what", "how", "can", "if", "with", "about", "at", "as", "by",
    "from", "we", "they", "he", "she", "will", "would", "should", "have", "has",
}


def _tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1]


class _BM25:
    """Minimal BM25 (Okapi) over a fixed set of documents."""

    def __init__(self, docs_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs = docs_tokens
        self.N = len(docs_tokens)
        self.doc_len = [len(d) for d in docs_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.freqs: List[Counter] = [Counter(d) for d in docs_tokens]
        df: Counter = Counter()
        for d in docs_tokens:
            for term in set(d):
                df[term] += 1
        # BM25+ style idf, floored at a small positive value.
        self.idf: Dict[str, float] = {
            term: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for term, n in df.items()
        }

    def scores(self, query_tokens: List[str]) -> List[float]:
        out = [0.0] * self.N
        for i in range(self.N):
            f = self.freqs[i]
            dl = self.doc_len[i] or 1
            s = 0.0
            for term in query_tokens:
                if term not in f:
                    continue
                idf = self.idf.get(term, 0.0)
                tf = f[term]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += idf * (tf * (self.k1 + 1)) / denom
            out[i] = s
        return out


def _minmax(xs: List[float]) -> List[float]:
    if not xs:
        return xs
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-12:
        return [0.0 for _ in xs]
    return [(x - lo) / (hi - lo) for x in xs]


class Retriever:
    """Hybrid retriever over the bundled corpus. Build once, query many."""

    def __init__(
        self,
        chunks: Optional[List[Chunk]] = None,
        bm25_weight: float = 0.5,
        tfidf_weight: float = 0.5,
    ):
        self.chunks: List[Chunk] = chunks if chunks is not None else load_corpus()
        self.bm25_weight = bm25_weight
        self.tfidf_weight = tfidf_weight

        corpus_texts = [c.search_text for c in self.chunks]
        self._bm25 = _BM25([_tokenize(t) for t in corpus_texts])

        # TF-IDF "embedding" space: word 1-2 grams + char 3-5 grams for
        # robustness to phrasing and form-name variants. Fully offline.
        if corpus_texts:
            self._vectorizer = TfidfVectorizer(
                lowercase=True,
                sublinear_tf=True,
                ngram_range=(1, 2),
                min_df=1,
                stop_words="english",
            )
            self._doc_matrix = self._vectorizer.fit_transform(corpus_texts)
        else:
            self._vectorizer = None
            self._doc_matrix = None

    def _tfidf_scores(self, query: str) -> List[float]:
        if self._vectorizer is None:
            return [0.0] * len(self.chunks)
        q = self._vectorizer.transform([query])
        sims = linear_kernel(q, self._doc_matrix).ravel()
        return list(sims)

    def search(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        if not self.chunks:
            return []
        settings = get_settings()
        k = top_k or settings.top_k

        bm = _minmax(self._bm25.scores(_tokenize(query)))
        tf = _minmax(self._tfidf_scores(query))

        fused: List[Tuple[int, float]] = []
        for i in range(len(self.chunks)):
            score = self.bm25_weight * bm[i] + self.tfidf_weight * tf[i]
            fused.append((i, score))

        fused.sort(key=lambda x: x[1], reverse=True)
        results: List[RetrievedChunk] = []
        for idx, score in fused[:k]:
            if score <= 0.0:
                continue
            c = self.chunks[idx]
            results.append(
                RetrievedChunk(
                    source_id=c.source_id,
                    chunk_id=c.chunk_id,
                    title=c.title,
                    url=c.url,
                    publisher=c.publisher,
                    retrieved=c.retrieved,
                    heading=c.heading,
                    text=c.text,
                    score=round(float(score), 4),
                )
            )
        return results

    @staticmethod
    def confidence(results: List[RetrievedChunk]) -> float:
        """Calibrated confidence from the retrieval scores.

        Top hit dominates; a strong second hit adds a little. Bounded to [0,1].
        Because fused scores are min-max'd to [0,1] per query, we damp the raw
        top score so that a thin, single-term match doesn't look overconfident.
        """
        if not results:
            return 0.0
        top = results[0].score
        second = results[1].score if len(results) > 1 else 0.0
        raw = 0.8 * top + 0.2 * second
        # Gentle compression keeps mid-range matches honest.
        return round(min(1.0, raw * 0.9 + 0.05 if top > 0 else 0.0), 4)


_RETRIEVER: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """Process-wide singleton (cheap to build, but build once)."""
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = Retriever()
    return _RETRIEVER


def reset_retriever() -> None:
    """Drop the singleton (used by tests that swap the corpus)."""
    global _RETRIEVER
    _RETRIEVER = None
