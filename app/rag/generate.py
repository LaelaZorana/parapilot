"""The Ask pipeline: scope -> retrieve -> confidence -> generate -> cite.

Produces a single ``AnswerEnvelope``. This is the anti-hallucination core:

  1. Out-of-scope / advice-seeking questions never reach retrieval, they refuse.
  2. Weak retrieval (confidence below threshold) refuses instead of guessing.
  3. Generation is citation-restricted; the answer keeps only markers that map
     to real retrieved chunks, and if nothing is grounded we refuse.
"""
from __future__ import annotations

from typing import List, Optional

from app.config import get_settings
from app.rag.citations import (
    build_citations,
    strip_unsupported_markers,
    used_marker_indices,
)
from app.rag.providers import get_provider
from app.rag.providers.base import Provider
from app.rag.retriever import Retriever, get_retriever
from app.safety.disclaimers import DISCLAIMER
from app.safety.refusal import build_refusal
from app.safety.scope import classify_scope
from app.schemas import AnswerEnvelope, AnswerKind, Escalation, RetrievedChunk

INSUFFICIENT = "INSUFFICIENT_CONTEXT"


def answer_question(
    question: str,
    retriever: Optional[Retriever] = None,
    provider: Optional[Provider] = None,
    top_k: Optional[int] = None,
    confidence_threshold: Optional[float] = None,
) -> AnswerEnvelope:
    """Run the full grounded pipeline and return a safe answer envelope."""
    settings = get_settings()
    retriever = retriever or get_retriever()
    provider = provider or get_provider()
    k = top_k or settings.top_k
    threshold = (
        confidence_threshold
        if confidence_threshold is not None
        else settings.confidence_threshold
    )

    question = (question or "").strip()
    if not question:
        return build_refusal(
            question, AnswerKind.REFUSAL_LOW_CONFIDENCE, "No question was provided."
        )

    # 1) Scope / UPL gate.
    scope = classify_scope(question)
    if not scope.in_scope:
        return build_refusal(question, scope.refusal_kind, scope.reason)

    # 2) Retrieve.
    results: List[RetrievedChunk] = retriever.search(question, top_k=k)
    confidence = Retriever.confidence(results)

    # 3) Confidence gate. If scope was uncertain (no explicit topic keyword),
    #    require a clearly strong hit and treat a miss as out-of-scope rather
    #    than merely low-confidence.
    effective_threshold = threshold
    miss_kind = AnswerKind.REFUSAL_LOW_CONFIDENCE
    if scope.needs_retrieval_check:
        effective_threshold = max(threshold, 0.45)
        miss_kind = AnswerKind.REFUSAL_SCOPE

    if not results or confidence < effective_threshold:
        return build_refusal(
            question,
            miss_kind,
            "Retrieval confidence {:.2f} was below the {:.2f} threshold.".format(
                confidence, effective_threshold
            ),
        )

    # 4) Citation-restricted generation.
    raw = provider.generate(question, results).strip()
    if raw == INSUFFICIENT or not raw:
        return build_refusal(
            question,
            AnswerKind.REFUSAL_LOW_CONFIDENCE,
            "The grounded sources did not contain enough to answer.",
        )

    # 5) Enforce citations: drop dead markers; require at least one real cite.
    answer_text = strip_unsupported_markers(raw, len(results))
    if not used_marker_indices(answer_text):
        return build_refusal(
            question,
            AnswerKind.REFUSAL_LOW_CONFIDENCE,
            "The answer could not be tied to a citation.",
        )

    citations = build_citations(answer_text, results)

    return AnswerEnvelope(
        kind=AnswerKind.GROUNDED,
        question=question,
        answer=answer_text,
        citations=citations,
        confidence=confidence,
        is_legal_information=True,
        disclaimer=DISCLAIMER,
        escalation=Escalation(),
        provider=provider.name,
    )
