"""Process engine: load + validate flows, walk steps and branches.

Loads the YAML flow(s), validates against the schema, and answers the questions
the UI needs: what's the next step, what branches are available here, what does
this step require, and is everything referenced actually defined.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.process.schema import Flow, Step

FLOWS_DIR = Path(__file__).resolve().parent / "flows"


class ProcessEngine:
    def __init__(self, flow: Flow) -> None:
        self.flow = flow
        self._steps: Dict[str, Step] = flow.step_map()
        self.validate()

    # ---- loading -----------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: Optional[Path] = None) -> "ProcessEngine":
        path = path or (FLOWS_DIR / "il_divorce.yaml")
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        flow = Flow(**data)
        return cls(flow)

    # ---- validation --------------------------------------------------------
    def validate(self) -> None:
        ids = set(self._steps)
        if self.flow.start not in ids:
            raise ValueError("start step '%s' is not defined" % self.flow.start)
        for step in self.flow.steps:
            for tr in step.transitions:
                if tr.to not in ids:
                    raise ValueError(
                        "step '%s' transitions to unknown step '%s'"
                        % (step.id, tr.to)
                    )
            for ht in step.help_triggers:
                if ht.to not in ids:
                    raise ValueError(
                        "step '%s' help_trigger points to unknown step '%s'"
                        % (step.id, ht.to)
                    )

    # ---- queries -----------------------------------------------------------
    def get(self, step_id: str) -> Optional[Step]:
        return self._steps.get(step_id)

    @property
    def start(self) -> Step:
        return self._steps[self.flow.start]

    def main_line(self) -> List[Step]:
        return self.flow.main_line()

    def subflows(self) -> List[Step]:
        return self.flow.subflows()

    def next_steps(self, step_id: str) -> List[Step]:
        """All steps directly reachable from this one (default + conditional)."""
        step = self.get(step_id)
        if not step:
            return []
        out, seen = [], set()
        for tr in step.transitions:
            if tr.to not in seen and tr.to in self._steps:
                seen.add(tr.to)
                out.append(self._steps[tr.to])
        return out

    def branches(self, step_id: str) -> List[Step]:
        """Conditional next-steps + help-trigger sub-flows for this step."""
        step = self.get(step_id)
        if not step:
            return []
        out, seen = [], set()
        for tr in step.transitions:
            if tr.when and tr.to in self._steps and tr.to not in seen:
                seen.add(tr.to)
                out.append(self._steps[tr.to])
        for ht in step.help_triggers:
            if ht.to in self._steps and ht.to not in seen:
                seen.add(ht.to)
                out.append(self._steps[ht.to])
        return out

    def verify_items(self) -> List[Dict[str, str]]:
        """Every place flagged ``verify: true`` — the human-review checklist."""
        items: List[Dict[str, str]] = []
        for step in self.flow.steps:
            if step.verify:
                items.append(
                    {
                        "step": step.id,
                        "what": "Step-level details need verification",
                        "source": "; ".join(step.citations) or "(see step)",
                    }
                )
            for f in step.required_forms:
                if f.verify or f.form_id == "verify-against-source":
                    items.append(
                        {
                            "step": step.id,
                            "what": "Form: %s (ID/details)" % f.name,
                            "source": f.source,
                        }
                    )
            for d in step.deadlines:
                if d.verify:
                    items.append(
                        {
                            "step": step.id,
                            "what": "Deadline: %s" % d.description,
                            "source": d.citation or d.basis,
                        }
                    )
        return items


_ENGINE: Optional[ProcessEngine] = None


def get_engine() -> ProcessEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ProcessEngine.from_yaml()
    return _ENGINE


def reset_engine() -> None:
    global _ENGINE
    _ENGINE = None
