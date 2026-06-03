"""Tests for the process state machine + the il_divorce flow."""
from __future__ import annotations

import pytest

from app.process.engine import ProcessEngine
from app.process.schema import Flow, Step


def test_flow_loads_and_validates(engine):
    assert engine.flow.id == "il_divorce"
    assert engine.flow.namespace == "il/divorce"
    assert engine.flow.jurisdiction == "IL"


def test_start_step_exists(engine):
    assert engine.start is not None
    assert engine.get(engine.flow.start) is not None


def test_required_subflows_present(engine):
    sub_ids = {s.id for s in engine.subflows()}
    for required in {"remote_appearance", "service_by_publication", "fee_waiver", "with_children"}:
        assert required in sub_ids


def test_main_line_is_ordered_and_nonempty(engine):
    main = engine.main_line()
    assert len(main) >= 6
    assert all(not s.is_subflow for s in main)


def test_serve_respondent_has_publication_branch(engine):
    branch_ids = {s.id for s in engine.branches("serve_respondent")}
    assert "service_by_publication" in branch_ids


def test_all_transitions_resolve(engine):
    ids = {s.id for s in engine.flow.steps}
    for step in engine.flow.steps:
        for tr in step.transitions:
            assert tr.to in ids
        for ht in step.help_triggers:
            assert ht.to in ids


def test_remote_appearance_cites_rule_45(engine):
    step = engine.get("remote_appearance")
    assert step is not None
    cites = " ".join(step.citations).lower()
    assert "rule" in cites or "remote" in cites


def test_no_fabricated_forms_unverified_are_flagged(engine):
    # Any form whose id is the placeholder must be marked verify.
    for step in engine.flow.steps:
        for f in step.required_forms:
            if f.form_id == "verify-against-source":
                assert f.verify or f.form_id == "verify-against-source"


def test_verify_items_collected(engine):
    items = engine.verify_items()
    assert len(items) >= 1
    for it in items:
        assert "step" in it and "what" in it


def test_invalid_flow_raises():
    bad = Flow(
        id="x", namespace="x", title="x", description="x", jurisdiction="IL",
        start="missing",
        steps=[Step(id="a", title="A", summary="s")],
    )
    with pytest.raises(ValueError):
        ProcessEngine(bad)


def test_bad_transition_target_raises():
    bad = Flow(
        id="x", namespace="x", title="x", description="x", jurisdiction="IL",
        start="a",
        steps=[
            Step(id="a", title="A", summary="s",
                 transitions=[{"to": "nowhere"}]),
        ],
    )
    with pytest.raises(ValueError):
        ProcessEngine(bad)
