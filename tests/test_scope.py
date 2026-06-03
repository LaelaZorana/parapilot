"""Tests for the out-of-scope / advice classifier."""
from __future__ import annotations

import pytest

from app.safety.scope import classify_scope
from app.schemas import AnswerKind


@pytest.mark.parametrize(
    "q",
    [
        "How do I serve my spouse in Illinois?",
        "What is the residency requirement for divorce?",
        "Can I appear by Zoom for my hearing?",
        "What goes in the parenting plan?",
        "How do I ask the court to waive fees?",
    ],
)
def test_in_scope_divorce_questions(q):
    res = classify_scope(q)
    assert res.in_scope is True


@pytest.mark.parametrize(
    "q",
    [
        "Should I file for divorce or stay married?",
        "Will I win custody of my kids?",
        "How much maintenance will I get?",
        "Do I have a good case?",
        "Which custody option should I choose?",
    ],
)
def test_advice_seeking_refused(q):
    res = classify_scope(q)
    assert res.in_scope is False
    assert res.refusal_kind == AnswerKind.REFUSAL_ADVICE


@pytest.mark.parametrize(
    "q",
    [
        "How do I file for divorce in California?",
        "What are Texas custody laws?",
        "How do I file for bankruptcy?",
        "How do I fight a speeding ticket?",
        "Can my landlord evict me?",
        "How do I apply for a green card?",
    ],
)
def test_out_of_scope_refused(q):
    res = classify_scope(q)
    assert res.in_scope is False
    assert res.refusal_kind == AnswerKind.REFUSAL_SCOPE


def test_procedural_should_is_not_advice():
    # "should I use" is procedural, not advice-seeking.
    res = classify_scope("What name should I use to join my Cook County Zoom hearing?")
    assert res.in_scope is True


def test_uncertain_question_defers_to_retrieval():
    # No explicit topic keyword, but no disqualifier either.
    res = classify_scope("How long must I live here before I can file?")
    assert res.in_scope is True
    assert res.needs_retrieval_check is True
