"""Run the anti-hallucination eval offline (SPEC §5).

    python -m app.eval.run_eval                # run + print table
    python -m app.eval.run_eval --json out.json
    python -m app.eval.run_eval --md docs.md   # write the README table fragment

Compares ParaPilot (grounded RAG + scope gate + citations) against a plain-LLM
baseline (no RAG) and reports the hallucination-rate delta plus per-metric
scores. Fully offline against the stub provider + bundled corpus.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import yaml

from app.config import ROOT_DIR
from app.eval.baseline import baseline_answer
from app.eval.metrics import (
    all_citations_real,
    cited_expected_source,
    contains_facts,
    is_hallucination,
    sentence_groundedness,
)
from app.rag.generate import answer_question
from app.schemas import AnswerEnvelope, AnswerKind

GOLD_PATH = Path(__file__).resolve().parent / "gold_set.yaml"

_REFUSAL_KINDS = {
    "refusal_advice": AnswerKind.REFUSAL_ADVICE,
    "refusal_scope": AnswerKind.REFUSAL_SCOPE,
}


def load_gold() -> List[dict]:
    with GOLD_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)["items"]


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def evaluate() -> Dict:
    gold = load_gold()
    grounded_items = [g for g in gold if g["type"] == "grounded"]
    refusal_items = [g for g in gold if g["type"].startswith("refusal")]

    # Counters for ParaPilot.
    pp = {
        "hallucinations": 0,
        "answer_correct": 0,
        "citation_correct": 0,
        "citations_real": 0,
        "grounded_supported": 0.0,  # summed groundedness over grounded answers
        "grounded_answered": 0,     # grounded items the system actually answered
        "refusal_correct": 0,
        "refusal_kind_correct": 0,
    }
    base = {"hallucinations": 0, "refusal_correct": 0, "answer_correct": 0}

    per_item: List[dict] = []

    for g in gold:
        q = g["question"]
        gtype = g["type"]

        env: AnswerEnvelope = answer_question(q)
        b_env: AnswerEnvelope = baseline_answer(q)

        # --- ParaPilot hallucination ---
        pp_hall = is_hallucination(env, gtype)
        if pp_hall:
            pp["hallucinations"] += 1
        # --- Baseline hallucination ---
        b_hall = is_hallucination(b_env, gtype)
        if b_hall:
            base["hallucinations"] += 1

        item = {
            "id": g["id"],
            "type": gtype,
            "pp_kind": env.kind.value,
            "pp_hallucination": pp_hall,
            "base_hallucination": b_hall,
        }

        if gtype == "grounded":
            if env.kind == AnswerKind.GROUNDED:
                pp["grounded_answered"] += 1
                ground = sentence_groundedness(env)
                pp["grounded_supported"] += ground
                item["groundedness"] = round(ground, 3)
                if all_citations_real(env):
                    pp["citations_real"] += 1
                if cited_expected_source(env, g["expect_source"]):
                    pp["citation_correct"] += 1
                if contains_facts(env.answer, g.get("expect_facts", [])):
                    pp["answer_correct"] += 1
                    item["answer_correct"] = True
                else:
                    item["answer_correct"] = False
            else:
                item["answer_correct"] = False  # refused a grounded Q
            # Baseline "answer correctness": it answers generically; count a hit
            # only if its prose happens to contain the expected facts.
            if contains_facts(b_env.answer, g.get("expect_facts", [])):
                base["answer_correct"] += 1

        else:  # refusal item
            want_kind = _REFUSAL_KINDS[gtype]
            if env.is_refusal:
                pp["refusal_correct"] += 1
                item["refused"] = True
                if env.kind == want_kind:
                    pp["refusal_kind_correct"] += 1
            else:
                item["refused"] = False
            if b_env.is_refusal:
                base["refusal_correct"] += 1

        per_item.append(item)

    n_grounded = len(grounded_items)
    n_refusal = len(refusal_items)
    n_total = len(gold)

    summary = {
        "counts": {
            "total": n_total,
            "grounded": n_grounded,
            "refusal": n_refusal,
        },
        "parapilot": {
            "hallucination_rate_pct": _pct(pp["hallucinations"], n_total),
            "answer_correctness_pct": _pct(pp["answer_correct"], n_grounded),
            "citation_accuracy_pct": _pct(pp["citation_correct"], n_grounded),
            "citations_real_pct": _pct(pp["citations_real"], max(1, pp["grounded_answered"])),
            "groundedness_pct": round(
                100.0 * pp["grounded_supported"] / max(1, pp["grounded_answered"]), 1
            ),
            "refusal_correctness_pct": _pct(pp["refusal_correct"], n_refusal),
            "refusal_kind_correctness_pct": _pct(pp["refusal_kind_correct"], n_refusal),
        },
        "baseline": {
            "hallucination_rate_pct": _pct(base["hallucinations"], n_total),
            "answer_correctness_pct": _pct(base["answer_correct"], n_grounded),
            "citation_accuracy_pct": 0.0,
            "groundedness_pct": 0.0,
            "refusal_correctness_pct": _pct(base["refusal_correct"], n_refusal),
        },
        "per_item": per_item,
    }
    return summary


def render_table(summary: Dict) -> str:
    pp = summary["parapilot"]
    base = summary["baseline"]
    c = summary["counts"]
    rows = [
        ("Hallucination rate", "{}%".format(base["hallucination_rate_pct"]),
         "{}%".format(pp["hallucination_rate_pct"]), "lower is better"),
        ("Answer correctness (grounded Qs)", "{}%".format(base["answer_correctness_pct"]),
         "{}%".format(pp["answer_correctness_pct"]), "higher is better"),
        ("Groundedness / faithfulness", "{}%".format(base["groundedness_pct"]),
         "{}%".format(pp["groundedness_pct"]), "higher is better"),
        ("Citation accuracy", "{}%".format(base["citation_accuracy_pct"]),
         "{}%".format(pp["citation_accuracy_pct"]), "higher is better"),
        ("Refusal correctness (out-of-scope/advice)", "{}%".format(base["refusal_correctness_pct"]),
         "{}%".format(pp["refusal_correctness_pct"]), "higher is better"),
    ]
    from app.config import get_settings
    s = get_settings()
    if s.provider == "stub":
        caption = ("Evaluated on {} gold Q&A ({} grounded, {} out-of-scope/advice), "
                   "fully offline on the deterministic stub provider.").format(
                       c["total"], c["grounded"], c["refusal"])
    else:
        model = (s.anthropic_model if s.provider == "anthropic"
                 else s.openai_model if s.provider == "openai" else s.provider)
        caption = ("Evaluated on {} gold Q&A ({} grounded, {} out-of-scope/advice). "
                   "ParaPilot's answers were generated by {} / {}; the plain-LLM baseline is a "
                   "deterministic ungrounded-LLM simulation (no retrieval, no citations).").format(
                       c["total"], c["grounded"], c["refusal"], s.provider, model)
    lines = []
    lines.append(caption)
    lines.append("")
    lines.append("| Metric | Plain LLM (no RAG) | ParaPilot (grounded) | |")
    lines.append("|---|---|---|---|")
    for name, b, p, note in rows:
        lines.append("| {} | {} | **{}** | {} |".format(name, b, p, note))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="ParaPilot anti-hallucination eval.")
    parser.add_argument("--json", type=str, default="", help="Write full results JSON here.")
    parser.add_argument("--md", type=str, default="", help="Write the README table fragment here.")
    args = parser.parse_args()

    summary = evaluate()
    table = render_table(summary)

    print("\n=== ParaPilot Anti-Hallucination Eval ===\n")
    print(table)
    print("\nDetail:")
    pp = summary["parapilot"]
    print("  ParaPilot   hallucination={}%  answer={}%  ground={}%  cite={}%  refuse={}%".format(
        pp["hallucination_rate_pct"], pp["answer_correctness_pct"],
        pp["groundedness_pct"], pp["citation_accuracy_pct"], pp["refusal_correctness_pct"]))
    base = summary["baseline"]
    print("  Baseline    hallucination={}%  answer={}%  refuse={}%".format(
        base["hallucination_rate_pct"], base["answer_correctness_pct"],
        base["refusal_correctness_pct"]))

    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("\nWrote JSON -> {}".format(args.json))
    if args.md:
        Path(args.md).write_text(table + "\n", encoding="utf-8")
        print("Wrote table -> {}".format(args.md))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
