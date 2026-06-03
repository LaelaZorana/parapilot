"""Tests for the anti-hallucination eval harness and metrics."""
from __future__ import annotations

from app.eval.baseline import baseline_answer
from app.eval.metrics import (
    contains_facts,
    is_hallucination,
    sentence_groundedness,
)
from app.eval.run_eval import evaluate, load_gold
from app.rag.generate import answer_question
from app.schemas import AnswerKind


def test_gold_set_size_in_range():
    gold = load_gold()
    assert 40 <= len(gold) <= 60, "gold set should have ~40-60 curated Q&A"


def test_gold_items_well_formed():
    for g in load_gold():
        assert g["id"] and g["question"] and g["type"]
        if g["type"] == "grounded":
            assert g.get("expect_source")
            assert g.get("expect_facts")


def test_contains_facts():
    assert contains_facts("at least 90 days of residency", ["90 days"])
    assert not contains_facts("no number here", ["90 days"])


def test_baseline_is_ungrounded_and_never_refuses():
    env = baseline_answer("Should I file for divorce?")
    assert env.kind == AnswerKind.GROUNDED  # it asserts, never refuses
    assert env.citations == []


def test_baseline_counts_as_hallucination_on_refusal_item():
    env = baseline_answer("Should I file for divorce?")
    assert is_hallucination(env, "refusal_advice") is True


def test_grounded_answer_not_hallucination():
    env = answer_question("What is the residency requirement?")
    assert is_hallucination(env, "grounded") is False
    assert sentence_groundedness(env) >= 0.5


def test_eval_summary_quality():
    """The headline result: grounded beats baseline by a wide margin."""
    summary = evaluate()
    pp = summary["parapilot"]
    base = summary["baseline"]

    # ParaPilot should hallucinate far less than the plain LLM baseline.
    assert base["hallucination_rate_pct"] > pp["hallucination_rate_pct"]
    assert pp["hallucination_rate_pct"] <= 10.0
    assert base["hallucination_rate_pct"] >= 90.0

    # Strong groundedness, citation accuracy, and refusal behavior.
    assert pp["groundedness_pct"] >= 80.0
    assert pp["citation_accuracy_pct"] >= 80.0
    assert pp["refusal_correctness_pct"] >= 90.0
    assert pp["answer_correctness_pct"] >= 80.0


def test_refusal_correctness_perfect_on_gold():
    summary = evaluate()
    # Every refusal item should be refused.
    assert summary["parapilot"]["refusal_correctness_pct"] == 100.0
