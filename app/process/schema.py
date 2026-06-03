"""Schema for the process state machine (SPEC §2).

A flow is a namespaced set of Step nodes. Each Step is curated, cited data — not
generated — which is what makes the roadmap hallucination-proof. Steps may be
ordinary process steps or conditional sub-flows (``is_subflow: true``).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class RequiredForm(BaseModel):
    form_id: str = Field(..., description="Catalog code/ID, or 'verify-against-source'.")
    name: str
    must_contain: List[str] = Field(default_factory=list)
    source: str
    verify: bool = Field(
        False, description="True if the ID/details still need human verification."
    )


class Deadline(BaseModel):
    description: str
    basis: str = ""
    citation: str = ""
    verify: bool = False


class Transition(BaseModel):
    to: str
    when: Optional[str] = Field(
        None, description="Condition label; None = default/next transition."
    )
    label: Optional[str] = None


class HelpTrigger(BaseModel):
    when: str
    to: str


class Step(BaseModel):
    id: str
    title: str
    summary: str
    is_subflow: bool = False
    trigger: Optional[str] = None  # for sub-flows: the condition that opens it
    preconditions: List[str] = Field(default_factory=list)
    required_actions: List[str] = Field(default_factory=list)
    required_forms: List[RequiredForm] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    who_to_contact: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    transitions: List[Transition] = Field(default_factory=list)
    help_triggers: List[HelpTrigger] = Field(default_factory=list)
    verify: bool = Field(
        False, description="Step-level flag: some specifics need verification."
    )


class Flow(BaseModel):
    id: str
    namespace: str
    title: str
    description: str
    jurisdiction: str
    start: str
    citations: List[str] = Field(default_factory=list)
    steps: List[Step]

    def step_map(self) -> dict:
        return {s.id: s for s in self.steps}

    def main_line(self) -> List[Step]:
        """The non-subflow steps, in declared order (the linear spine)."""
        return [s for s in self.steps if not s.is_subflow]

    def subflows(self) -> List[Step]:
        return [s for s in self.steps if s.is_subflow]
