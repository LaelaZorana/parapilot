# ParaPilot — Illinois Divorce Procedural Navigator (MVP Spec)

> Your "legal GPS" for an Illinois divorce: plain-English, step-by-step, **grounded and cited** — legal **information, not legal advice.**

This spec is the single source of truth. Build exactly to it, to the same deploy-ready bar as the other portfolio projects.

## 0. Positioning & guardrails (read first)
- **Audience:** self-represented litigants AND people who have a lawyer but can't ask them every procedural question.
- **The validated gap:** existing tools do guided FORMS (ILAO / A2J Author) or reactive, general-civil case tracking (Courtroom5). Nobody does a **proactive, Illinois-family-law-specific conditional roadmap**. We own that.
- **Hard guardrails (non-negotiable; modeled on FTC v. DoNotPay, $193K, 2025):**
  - Frame everything as **"legal information, not legal advice."** Never "what you should do" → instead "here are your options and the rule that applies."
  - Never claim to be / replace a lawyer. No lawyer-equivalence language anywhere.
  - **Every substantive answer MUST carry a citation** to an authoritative source. Weak/empty retrieval → say so, refuse, escalate.
  - Out-of-scope (non-IL, non-divorce, or advice-seeking) → refuse + escalate to legal aid (ILAO).
  - Persistent disclaimer + one-click "Find legal help" (ILAO / Illinois Lawyer Finder).

## 1. Architecture — hybrid (state machine + grounded RAG)
Two cooperating layers:
1. **PROCESS MODEL (deterministic backbone):** the IL divorce process as a data-driven **state machine** (curated, cited, version-controlled). Hallucination-proof because it's curated data, not generation. Drives the visual roadmap, "what's next," deadlines, required forms, who-to-call.
2. **GROUNDED RAG (the long tail):** answers free-form questions by retrieving from the ingested IL corpus + (optional) case law, with **citation-restricted generation**, confidence, and refusal.

The state machine is the spine; RAG handles questions the spine doesn't directly answer. **Both always cite sources.**

## 2. Process-model schema (jurisdiction procedure as data)
Namespaced `il/divorce`. Example `Step` node (YAML):
```yaml
id: serve_respondent
title: "Serve your spouse (the respondent)"
summary: "After filing, you must formally notify your spouse that a case has started."
preconditions: [petition_filed]
required_forms:
  - form_id: "verify-against-source"      # do NOT invent; pull real ID or mark verify:true
    name: "Summons"
    must_contain: ["case number", "names of both parties", "respondent's address"]
    source: "https://www.illinoiscourts.gov/documents-and-forms/approved-forms/"
deadlines:
  - description: "Service generally must be completed before the first court date / before default can be sought"
    basis: "verify against ILAO / local rule"
    citation: "https://www.illinoislegalaid.org/legal-information/getting-divorce"
who_to_contact: "County sheriff's office, or a licensed special process server"
citations: ["https://www.illinoislegalaid.org/legal-information/getting-divorce"]
transitions:
  - to: respondent_response
  - when: "respondent cannot be located"
    to: service_by_publication
help_triggers:
  - when: "can't afford the filing/service fee"
    to: fee_waiver_subflow
```
Conditional **sub-flows are first-class.** Required for the MVP: `remote_appearance`, `service_by_publication`, `fee_waiver`, and `with_children` (allocation of parental responsibilities / parenting plan). Include the remote-appearance branch explicitly:
```yaml
id: remote_appearance
title: "Appear remotely (Zoom) instead of in person"
trigger: "cannot attend in person"
summary: "Illinois permits remote appearances for many civil hearings (Ill. Sup. Ct. Rule 45). You must follow your specific court's procedure to request it."
required_actions:
  - "Check your court/judge's remote-appearance policy (each circuit differs)"
  - "Submit any required request form/email by the court's stated deadline"
  - "Test the video link before the hearing"
who_to_contact: "the courtroom clerk / call center for your judicial circuit"
citations: ["Ill. Sup. Ct. Rule 45", "https://www.cookcountycourtil.gov/about/remote-court-proceedings"]
```
**Build the full IL divorce flow grounded in the cited sources. Do NOT invent form IDs, fees, or deadlines — pull them from the sources or mark `verify: true` with the source URL to check.**

## 3. Corpus & ingestion
Authoritative IL sources (cite every chunk with URL + retrieved date):
- ILAO "Getting a divorce": https://www.illinoislegalaid.org/legal-information/getting-divorce
- IL Supreme Court approved/standardized forms: https://www.illinoiscourts.gov/documents-and-forms/approved-forms/
- Ill. Sup. Ct. Rule 45 (remote appearances)
- Cook County remote proceedings: https://www.cookcountycourtil.gov/about/remote-court-proceedings
- Extensible: ILCS 750 (Illinois Marriage and Dissolution of Marriage Act); local circuit rules (e.g., DuPage/18th, Cook)
- Case law (OPTIONAL, pluggable, OFF by default): CourtListener REST API / MCP (https://www.courtlistener.com/help/api/rest/) — works fully without it.

Ingestion pipeline (`app/rag/ingest/`): fetch → clean → chunk → embed → store. **Ship an OFFLINE SEED SNAPSHOT** (small bundled corpus in `data/corpus/`) so the app runs with no network/keys. `make ingest` refreshes from live sources.

## 4. Retrieval & generation (anti-hallucination)
- Hybrid retrieval (TF-IDF/BM25 + embeddings; lean, offline-friendly fallback like the other repos).
- **Citation-restricted generation:** the model may only assert what retrieved chunks support; every claim → inline clickable citation to its source chunk.
- **Confidence score**; below threshold or no good chunk → **refuse** ("I don't have a grounded answer for that — here's how to reach legal aid").
- **Out-of-scope classifier:** non-IL / non-divorce / advice-seeking → refuse + escalate.
- **Provider interface:** offline deterministic STUB (grounded *extractive* answers from retrieved chunks) + Anthropic/OpenAI when keyed. Tests + demo run on the stub.

## 5. Anti-hallucination eval (first-class artifact)
- Gold set: ~40–60 curated IL-divorce Q&A, each with a known answer + authoritative citation, in `app/eval/gold_set.yaml`.
- Metrics: groundedness/faithfulness (is every claim supported by a retrieved source? RAGAS-style), citation accuracy, answer correctness, and **refusal correctness** (does it correctly refuse out-of-scope/advice questions?).
- **Baseline comparison:** run the same questions through a plain LLM (no RAG) and report the hallucination-rate delta. Publish the table in the README — this is the trust signal and the portfolio centerpiece.
- `make eval` runs offline against the stub + gold set.

## 6. UPL / safety implementation
- Every response object carries: `disclaimer`, `citations[]`, `is_legal_information: true`, and an `escalation` block.
- Refusal templates for advice-seeking: "I can explain your options and the rule that applies, but I can't tell you which to choose — here's how to reach a lawyer / legal aid."
- Footer + first-run modal: "ParaPilot provides legal information, not legal advice…" + ILAO link.

## 7. Tech stack & UI
- **Backend:** FastAPI (Python 3.9-compatible, like the other repos), SQLite (progress / saved matter).
- **Frontend:** server-rendered FastAPI + Jinja + htmx, styled with the **shared design system — Tailwind, clean modern SaaS, light + dark, indigo/violet accent, Inter, generous whitespace.** Two main views:
  1. **ROADMAP:** a visual stepper/flowchart of the divorce process. Click a step → panel with summary, required forms + *what each must contain*, deadlines, who-to-call, citations, and next/branch options. Conditional branches visible (children? remote appearance? can't locate spouse?).
  2. **ASK:** a grounded chat. Answers show **inline citations + a confidence indicator + the disclaimer**; out-of-scope → visible refusal + escalation card.
- **This is the flagship — it must look genuinely polished.** (Claude will design-verify via the live preview/screenshot loop after the build.)

## 8. House style (same as the other portfolio repos)
Offline-first (no keys needed), Docker + docker-compose, GitHub Actions CI, pytest green offline, case-study README (Problem → Solution → Results + mermaid + the eval table), `.env.example`, `.gitignore`, LICENSE MIT "Copyright (c) 2026 Laela Zorana", Makefile (`make demo`, `make eval`, `make ingest`, `make test`), deploy config (Render/Fly/HF Spaces). **No "Claude"/assistant attribution anywhere. No git init/commit/push. No deploy.**

## 9. Target file structure
```
parapilot/
  app/
    main.py  config.py  db.py  models.py  schemas.py  deps.py
    process/  engine.py  schema.py  flows/il_divorce.yaml (+ subflow files)
    rag/  ingest/  retriever.py  generate.py  citations.py  providers/{base,stub,anthropic,openai}.py
    safety/  scope.py  refusal.py  disclaimers.py
    eval/  gold_set.yaml  run_eval.py  metrics.py
    templates/  static/   # Tailwind design system
  data/corpus/            # offline seed snapshot (gitignored large; keep a small seed)
  tests/
  Dockerfile  docker-compose.yml  .github/workflows/ci.yml  Makefile
  README.md  LICENSE  .env.example  .gitignore  pyproject.toml  requirements*.txt
```

## 10. Out of scope / verify-before-publish
- Exact IL form IDs, fees, and statutory deadlines **must be verified against the live sources during ingestion** (mark `verify: true` where uncertain; never fabricate).
- California/Colorado and other use cases = phase 2.
- Content is legal information pending legal-aid review; not a lawyer; not legal advice.
