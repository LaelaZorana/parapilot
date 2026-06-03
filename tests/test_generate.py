"""Tests for the end-to-end grounded answer pipeline."""
from __future__ import annotations

import pytest

from app.rag.generate import answer_question
from app.schemas import AnswerKind


def test_grounded_answer_has_citations():
    env = answer_question("How long must I live in Illinois before getting a divorce?")
    assert env.kind == AnswerKind.GROUNDED
    assert env.citations, "grounded answer must carry citations"
    assert env.confidence > 0
    assert "90 days" in env.answer


def test_every_grounded_claim_is_cited():
    env = answer_question("What is service by publication?")
    assert env.kind == AnswerKind.GROUNDED
    # The answer text must contain at least one [n] marker.
    assert "[" in env.answer and "]" in env.answer


def test_citations_resolve_to_real_sources():
    env = answer_question("Can I appear by Zoom for my hearing?")
    assert env.kind == AnswerKind.GROUNDED
    for c in env.citations:
        assert c.url.startswith("http")
        assert c.source_id and c.chunk_id


def test_advice_question_refuses():
    env = answer_question("Should I file for divorce or try to reconcile?")
    assert env.kind == AnswerKind.REFUSAL_ADVICE
    assert env.citations == []
    assert env.escalation.legal_aid_url


def test_out_of_scope_refuses():
    env = answer_question("How do I file for divorce in California?")
    assert env.kind == AnswerKind.REFUSAL_SCOPE


def test_off_topic_refuses():
    env = answer_question("How do I bake sourdough bread?")
    assert env.is_refusal


def test_every_response_carries_disclaimer_and_flag():
    for q in [
        "How do I serve my spouse?",
        "Should I settle?",
        "How do I file for divorce in Texas?",
    ]:
        env = answer_question(q)
        assert env.is_legal_information is True
        assert env.disclaimer
        assert env.escalation.legal_aid_url


def test_empty_question_refuses():
    env = answer_question("   ")
    assert env.is_refusal


def test_grounded_confidence_within_bounds():
    env = answer_question("What are the grounds for divorce in Illinois?")
    assert 0.0 <= env.confidence <= 1.0
