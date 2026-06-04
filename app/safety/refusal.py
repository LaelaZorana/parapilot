"""Refusal templates: build a safe ``AnswerEnvelope`` for any non-answer.

Three refusal shapes (SPEC §4, §6):
  * advice-seeking  -> "I can explain your options and the rule, but I can't
                        tell you which to choose."
  * out-of-scope    -> non-IL / non-divorce.
  * low-confidence  -> retrieval too weak to ground an answer.

Every refusal still carries the disclaimer + escalation block.
"""
from __future__ import annotations

from app.safety.disclaimers import DISCLAIMER
from app.schemas import AnswerEnvelope, AnswerKind, Escalation

_ADVICE_TEXT = (
    "I can explain your options and the rule that applies, but I can't tell you "
    "which choice to make or predict how a judge will rule, that's legal advice, "
    "and ParaPilot provides legal information only. For guidance on your specific "
    "situation, please reach out to a licensed Illinois attorney or legal aid."
)

_SCOPE_TEXT = (
    "ParaPilot only covers the Illinois divorce (dissolution of marriage) process. "
    "Your question looks like it's outside that scope, so I don't have a grounded "
    "answer for it. For help with this, please contact a lawyer or legal aid."
)

_LOW_CONF_TEXT = (
    "I don't have a grounded answer for that in my Illinois divorce sources, so I "
    "won't guess. You can rephrase to focus on the Illinois divorce process, or "
    "reach out to legal aid for help with your specific question."
)


def build_refusal(question: str, kind: AnswerKind, detail: str = "") -> AnswerEnvelope:
    """Construct a refusal envelope for the given refusal ``kind``."""
    if kind == AnswerKind.REFUSAL_ADVICE:
        answer = _ADVICE_TEXT
    elif kind == AnswerKind.REFUSAL_LOW_CONFIDENCE:
        answer = _LOW_CONF_TEXT
    else:
        kind = AnswerKind.REFUSAL_SCOPE
        answer = _SCOPE_TEXT

    if detail:
        answer = answer + "\n\n(Why: " + detail + ")"

    return AnswerEnvelope(
        kind=kind,
        question=question,
        answer=answer,
        citations=[],
        confidence=0.0,
        is_legal_information=True,
        disclaimer=DISCLAIMER,
        escalation=Escalation(),
        provider="safety",
    )
