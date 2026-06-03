"""Deterministic, offline STUB provider — grounded *extractive* answers.

This is the default provider. It does NOT generate free text; it can only
*select and quote* sentences from the retrieved context, then attach the
citation marker of the passage each sentence came from. That makes it
structurally impossible to hallucinate: every word in the answer is copied from
a cited source chunk. This is exactly what we want the offline demo and the
eval to run on.

Selection: score each candidate sentence by query-term overlap (with the
passage's own retrieval rank as a prior), take the best few across the top
passages, and order them by passage rank for a readable answer.
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

from app.rag.providers.base import Provider
from app.schemas import RetrievedChunk

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(0-9'\"])")
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "be", "do", "does", "did", "i", "my", "me", "you", "your", "it", "this",
    "that", "what", "how", "can", "if", "with", "about", "at", "as", "by",
    "from", "we", "they", "will", "would", "should", "have", "has", "must",
}


def _words(text: str) -> List[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOP and len(w) > 1]


def _split_sentences(text: str) -> List[str]:
    parts = _SENT_SPLIT.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


class StubProvider(Provider):
    name = "stub"

    # Tunables.
    max_sentences = 4
    min_overlap = 1  # a kept sentence must share at least this many query terms

    # When the top hit dominates the rest by this ratio, treat the whole top
    # chunk as the answer passage and quote it in full. This rescues "when/how"
    # questions whose answer sentence shares no keywords with the question.
    dominant_ratio = 1.6

    def generate(self, question: str, context: List[RetrievedChunk]) -> str:
        if not context:
            return "INSUFFICIENT_CONTEXT"

        q_terms = set(_words(question))
        if not q_terms:
            # No usable query terms; fall back to the single best passage lead.
            lead = _split_sentences(context[0].text)
            return (lead[0] + " [1]") if lead else "INSUFFICIENT_CONTEXT"

        # Dominant-top-chunk shortcut: if passage 1 clearly outscores passage 2,
        # quote the whole top passage (it's unambiguously the relevant source).
        if len(context) >= 1:
            top_score = context[0].score
            second_score = context[1].score if len(context) > 1 else 0.0
            dominates = top_score > 0 and (
                second_score <= 0 or top_score / max(second_score, 1e-9) >= self.dominant_ratio
            )
            if dominates:
                sents = _split_sentences(context[0].text)
                if sents:
                    kept = sents[: self.max_sentences]
                    body = " ".join(
                        s if s.endswith((".", "!", "?")) else s + "." for s in kept
                    )
                    return body + " [1]"

        # Weight query terms by specificity: a term that appears in few passages
        # is more discriminating (e.g. "90", "publication") than one in many
        # ("divorce"). This keeps the lead sentence on-topic for the question.
        df: Dict[str, int] = {t: 0 for t in q_terms}
        for chunk in context:
            ctext = set(_words(chunk.text))
            for t in q_terms:
                if t in ctext:
                    df[t] += 1
        n = len(context)
        weight = {t: math.log(1 + n / (1 + df[t])) + 0.1 for t in q_terms}

        # Gather candidate sentences across passages with their citation index.
        candidates: List[Tuple[float, int, int, str]] = []  # (score, passage_i, sent_j, sent)
        for pi, chunk in enumerate(context):
            rank_prior = 1.0 / (1.0 + pi)  # earlier passages weighted higher
            for sj, sent in enumerate(_split_sentences(chunk.text)):
                s_terms = set(_words(sent))
                matched = q_terms & s_terms
                if len(matched) < self.min_overlap:
                    continue
                # Specificity-weighted coverage, normalized by total query weight.
                hit_weight = sum(weight[t] for t in matched)
                coverage = hit_weight / sum(weight.values())
                pos_prior = 1.0 / (1.0 + sj)
                score = coverage + 0.15 * rank_prior + 0.05 * pos_prior
                candidates.append((score, pi, sj, sent))

        if not candidates:
            # Query terms matched the passage (that's why it was retrieved) but
            # not any single sentence strongly — quote the top passage's lead so
            # we still ground rather than refuse.
            lead = _split_sentences(context[0].text)
            return (lead[0] + " [1]") if lead else "INSUFFICIENT_CONTEXT"

        # Pick the best N, but de-duplicate identical sentences.
        candidates.sort(key=lambda x: x[0], reverse=True)
        chosen: List[Tuple[int, int, str]] = []
        seen = set()
        for _, pi, sj, sent in candidates:
            if sent in seen:
                continue
            seen.add(sent)
            chosen.append((pi, sj, sent))
            if len(chosen) >= self.max_sentences:
                break

        # Order chosen sentences by (passage rank, sentence order) for flow.
        chosen.sort(key=lambda x: (x[0], x[1]))

        out = []
        for pi, _sj, sent in chosen:
            marker = "[{}]".format(pi + 1)
            sent = sent if sent.endswith((".", "!", "?")) else sent + "."
            out.append("{} {}".format(sent, marker))
        return " ".join(out)
