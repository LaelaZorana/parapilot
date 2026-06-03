"""Out-of-scope classifier (SPEC §4, §6).

Deterministic, dependency-free, and explainable. ParaPilot only answers
questions that are:
  * about Illinois (or jurisdiction-neutral procedure), AND
  * about divorce / dissolution of marriage / related family-law procedure, AND
  * informational ("what are my options / what's the rule") rather than
    advice-seeking ("what should I do / will I win").

Anything else -> refuse + escalate. Because the gold-set refusal metric depends
on this, the rules are intentionally transparent rather than ML-based.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from app.schemas import AnswerKind

# --- Topic: is this about divorce / IL family-law procedure? ----------------
DIVORCE_TERMS = [
    "divorce", "dissolution", "marriage", "spouse", "spousal", "marital",
    "petition", "respondent", "petitioner", "summons", "serve", "service",
    "custody", "parental responsibilit", "parenting plan", "parenting time",
    "child support", "maintenance", "alimony", "fee waiver", "filing fee",
    "waive", "waiver", "court fee", "court fees",
    "judgment", "default", "publication", "appearance", "financial affidavit",
    "irreconcilable", "separation", "annulment", "civil union", "remote",
    "zoom", "hearing", "court date", "imdma", "750 ilcs", "allocation",
    "parenting", "settlement agreement", "uncontested", "contested",
    "lived apart", "living apart", "live apart", "separate and apart",
    "appear by video", "appear remotely", "appear by phone", "by video",
    "parenting education", "parenting class", "diligent search", "prove-up",
    "no-fault", "no fault", "grounds for divorce", "ex-spouse",
]

# Other legal areas that are explicitly NOT divorce -> out of scope.
OTHER_LEGAL_TOPICS = [
    "bankruptcy", "immigration", "visa", "green card", "criminal", "dui",
    "speeding ticket", "traffic ticket", "landlord", "tenant", "eviction",
    "personal injury", "car accident", "patent", "trademark", "copyright",
    "employment discrimination", "wrongful termination", "will ", "a will",
    "my will", "estate plan", "probate", "tax return", "taxes", "incorporat",
    "llc", "expungement", "small business", "start a business", "lawsuit",
    "sue someone", "speeding", "arrest",
]

# --- Jurisdiction: other US states -> out of scope (we only do Illinois) -----
OTHER_STATES = [
    "california", "colorado", "new york", "texas", "florida", "ohio",
    "michigan", "indiana", "wisconsin", "iowa", "missouri", "kentucky",
    "georgia", "arizona", "nevada", "washington", "oregon", "pennsylvania",
    "new jersey", "massachusetts", "virginia", "north carolina",
    "south carolina", "tennessee", "minnesota", "maryland", "louisiana",
]
IL_TERMS = ["illinois", "cook county", "dupage", "il ", "750 ilcs", "imdma"]

# --- Intent: advice-seeking phrasing (we explain options, not choices) -------
# Tuned to catch "tell me what to do / predict my outcome" without snagging
# procedural "what should I use / where should I file" questions, which are
# legitimate information requests.
ADVICE_PATTERNS = [
    r"\bwhat should i do\b",
    r"\bwhat would you do\b",
    # "should i" only when asking whether to take a substantive action / choice.
    r"\bshould i (file|divorce|settle|agree|sign|hire|fight|leave|stay|"
    r"accept|reject|take|get|ask for|go to court|represent)\b",
    r"\bdo you think i\b",
    r"\bwhat do you recommend\b",
    r"\bwhat'?s best for me\b",
    r"\bwhat is best for me\b",
    r"\bwhich (option |one |custody |arrangement )?should i (choose|pick|file|take|select)\b",
    r"\bshould i choose\b",
    r"\bwill i (win|lose|get|keep)\b",
    r"\bdo i have a (good |strong |bad )?case\b",
    r"\bcan i win\b",
    r"\bam i going to (win|lose)\b",
    r"\bhow much (will|would) i (get|pay|owe|receive)\b",
    r"\bwho will (win|get custody)\b",
    r"\bwhat are my chances\b",
    r"\bis it worth it\b",
    r"\bshould i hire\b",
    r"\bwhat would happen (to me )?if i\b",
]


@dataclass
class ScopeResult:
    in_scope: bool
    refusal_kind: Optional[AnswerKind] = None
    reason: str = ""
    matched: Optional[str] = None
    # True when no explicit topic keyword matched but nothing disqualifies the
    # question either. The caller should defer to retrieval confidence: a strong
    # hit in the IL-divorce corpus confirms scope; a weak hit refuses.
    needs_retrieval_check: bool = False


def _contains_any(text: str, terms: List[str]) -> Optional[str]:
    for t in terms:
        if t in text:
            return t.strip()
    return None


def _matches_any(text: str, patterns: List[str]) -> Optional[str]:
    for p in patterns:
        if re.search(p, text):
            return p
    return None


def classify_scope(question: str) -> ScopeResult:
    """Return whether the question is in scope, and if not, why."""
    q = " " + question.lower().strip() + " "

    on_topic = _contains_any(q, DIVORCE_TERMS)

    # 1) Advice-seeking: refuse even if it's about IL divorce. This is the
    #    UPL line — we won't tell someone which choice to make or predict
    #    outcomes. We check this first so on-topic advice questions still refuse.
    advice = _matches_any(q, ADVICE_PATTERNS)
    if advice and on_topic:
        return ScopeResult(
            in_scope=False,
            refusal_kind=AnswerKind.REFUSAL_ADVICE,
            reason="The question asks for advice or a prediction about a specific case.",
            matched=advice,
        )

    # 2) Wrong jurisdiction: mentions another US state and not Illinois.
    other_state = _contains_any(q, OTHER_STATES)
    has_il = _contains_any(q, IL_TERMS)
    if other_state and not has_il:
        return ScopeResult(
            in_scope=False,
            refusal_kind=AnswerKind.REFUSAL_SCOPE,
            reason="ParaPilot only covers Illinois; the question is about another state.",
            matched=other_state,
        )

    # 3) Wrong topic: clearly a different area of law.
    other_topic = _contains_any(q, OTHER_LEGAL_TOPICS)
    if other_topic and not on_topic:
        return ScopeResult(
            in_scope=False,
            refusal_kind=AnswerKind.REFUSAL_SCOPE,
            reason="The question is about a different area of law, not Illinois divorce.",
            matched=other_topic,
        )

    # 4) Generic advice phrasing with no clear divorce topic -> scope refusal.
    if advice and not on_topic:
        return ScopeResult(
            in_scope=False,
            refusal_kind=AnswerKind.REFUSAL_ADVICE,
            reason="The question asks for personal advice rather than legal information.",
            matched=advice,
        )

    # 5) No explicit divorce keyword, but nothing disqualifies it either
    #    (no other state, no other legal topic, no advice phrasing). Defer to
    #    retrieval: if the IL-divorce corpus answers it strongly, it's in scope;
    #    if not, the confidence gate refuses. This handles legitimate phrasings
    #    like "How long must I live here before I can file?".
    if not on_topic:
        return ScopeResult(
            in_scope=True,
            needs_retrieval_check=True,
            reason="No explicit topic term; deferring to retrieval confidence.",
        )

    return ScopeResult(in_scope=True, reason="In scope: Illinois divorce procedure.")
