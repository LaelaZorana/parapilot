"""Eval metrics (SPEC §5).

All metrics are computable offline against the stub + corpus:

  * groundedness / faithfulness: is every sentence in the answer backed by a
    cited source chunk? (RAGAS-style, computed by checking that each answer
    sentence has strong token overlap with at least one cited chunk's text)
  * citation accuracy: did the answer cite the EXPECTED source, and are all
    emitted citations real (resolve to retrieved chunks)?
  * answer correctness: does the grounded answer contain the expected fact(s)?
  * refusal correctness: did the system refuse exactly the questions it should,
    with the right refusal kind?
  * hallucination: for the baseline comparison, an answer that asserts content
    NOT supported by the corpus (ungrounded) counts as a hallucination. A
    correct refusal is NOT a hallucination.
"""
from __future__ import annotations

import re
from typing import List, Sequence

from app.schemas import AnswerEnvelope, AnswerKind

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "be", "do", "does", "did", "it", "this", "that", "with", "you", "your",
    "can", "if", "at", "as", "by", "from", "will", "must", "have", "has",
}
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _tok(text: str) -> set:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOP and len(w) > 1}


def contains_facts(answer: str, facts: Sequence[str]) -> bool:
    """Answer correctness: all expected fact substrings present (case-insensitive)."""
    low = answer.lower()
    return all(f.lower() in low for f in facts)


def cited_expected_source(env: AnswerEnvelope, expected_source: str) -> bool:
    return any(c.source_id == expected_source for c in env.citations)


def _claims_with_markers(answer: str) -> List[tuple]:
    """Split an answer into (claim_text, [marker, ...]) units.

    A citation marker [n] annotates the text that PRECEDES it (the claim, then
    its source). We therefore cut the answer at each marker and pair the run of
    text before it with that marker. Trailing text with no marker is its own
    (unsupported) claim.
    """
    units: List[tuple] = []
    last = 0
    for m in re.finditer(r"\[(\d+)\]", answer):
        claim = answer[last : m.start()]
        # Consecutive markers (e.g. "[1][2]") share the preceding claim.
        if not claim.strip() and units:
            units[-1][1].append(m.group(1))
        else:
            units.append((claim, [m.group(1)]))
        last = m.end()
    tail = answer[last:]
    if tail.strip():
        units.append((tail, []))
    return units


def sentence_groundedness(env: AnswerEnvelope, overlap_threshold: float = 0.5) -> float:
    """Fraction of cited claims supported by the text of the chunk they cite.

    Each "claim [n]" unit must share at least ``overlap_threshold`` of its
    content tokens with the cited chunk's snippet. Claims with no citation are
    unsupported (count against groundedness). Refusals assert nothing.
    """
    if env.kind != AnswerKind.GROUNDED:
        return 1.0  # refusals assert nothing, so vacuously grounded

    units = _claims_with_markers(env.answer)
    if not units:
        return 0.0

    snip_tokens = {c.marker: _tok(c.snippet) for c in env.citations}

    scored = 0
    supported = 0
    for claim, markers in units:
        claim_tok = _tok(claim)
        if not claim_tok:
            continue  # nothing asserted in this unit; don't score it
        scored += 1
        ok = False
        for mk in markers:
            chunk_tok = snip_tokens.get(mk, set())
            if not chunk_tok:
                continue
            overlap = len(claim_tok & chunk_tok) / max(1, len(claim_tok))
            if overlap >= overlap_threshold:
                ok = True
                break
        if ok:
            supported += 1
    return supported / scored if scored else 0.0


def all_citations_real(env: AnswerEnvelope) -> bool:
    """Every emitted citation has a resolvable URL/source (no dangling cites)."""
    return all(c.url and c.source_id and c.chunk_id for c in env.citations)


def is_hallucination(env: AnswerEnvelope, expected_type: str) -> bool:
    """Did the system assert ungrounded content?

    - A correct refusal is never a hallucination.
    - A grounded answer with no citations, or with low groundedness, is a
      hallucination (it asserted something it couldn't support).
    - Answering a question that should have been refused (advice/scope) with
      asserted content is a hallucination.
    """
    if env.kind == AnswerKind.GROUNDED:
        if expected_type != "grounded":
            # Should have refused but instead asserted content.
            return True
        if not env.citations:
            return True
        return sentence_groundedness(env) < 0.5
    # Any refusal asserts nothing substantive -> not a hallucination.
    return False
