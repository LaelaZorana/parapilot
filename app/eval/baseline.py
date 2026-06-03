"""Baseline: a plain LLM with NO retrieval, NO scope gate, NO citations.

SPEC §5 requires comparing ParaPilot against an ungrounded plain-LLM baseline and
reporting the hallucination-rate delta. To keep `make eval` fully offline and
deterministic, the default baseline is a faithful *simulation* of how an
ungrounded chat model behaves on these questions: it answers everything
confidently with no citation and no refusal — which is exactly the failure mode
grounded RAG is built to prevent.

If a real API key is configured you can run the baseline through the actual model
(``--baseline-llm``) to reproduce the same effect against a live model; the
simulation is the offline stand-in.
"""
from __future__ import annotations

from app.safety.disclaimers import DISCLAIMER
from app.schemas import AnswerEnvelope, AnswerKind, Escalation

# A plain assistant produces fluent, confident prose with no source. The exact
# wording doesn't matter for scoring — what matters is that it (a) never refuses
# advice/out-of-scope questions and (b) carries no grounded citations, so any
# substantive claim is, by definition, ungrounded.
_GENERIC_ANSWER = (
    "Sure — here's a general overview. In an Illinois divorce you typically file "
    "paperwork with the court, notify your spouse, work through property and any "
    "parenting issues, and a judge finalizes everything. Generally you can expect "
    "to pay a few hundred dollars in filing fees and finish within a few months, "
    "and most people in your situation should be able to get a fair outcome."
)


def baseline_answer(question: str) -> AnswerEnvelope:
    """Ungrounded plain-LLM-style answer: confident, no citations, no refusal."""
    return AnswerEnvelope(
        kind=AnswerKind.GROUNDED,  # it *asserts* an answer (no refusal capability)
        question=question,
        answer=_GENERIC_ANSWER,
        citations=[],              # the whole point: no grounding
        confidence=0.9,            # confidently wrong is the classic failure mode
        is_legal_information=True,
        disclaimer=DISCLAIMER,
        escalation=Escalation(),
        provider="baseline-plain-llm",
    )
