"""Provider interface for citation-restricted generation."""
from __future__ import annotations

import abc
from typing import List

from app.schemas import RetrievedChunk


# The shared system contract for ALL providers: answer only from the numbered
# context, cite inline, refuse if unsupported, never give advice. The stub
# enforces this structurally (it can only copy from the context); the LLM
# providers receive it as the system prompt.
SYSTEM_CONTRACT = (
    "You are ParaPilot, an Illinois divorce procedural navigator. You provide "
    "legal INFORMATION, not legal advice.\n"
    "Rules you must follow exactly:\n"
    "1. Answer ONLY using the numbered CONTEXT passages provided. Do not add "
    "facts, form names, fees, deadlines, or statutes that are not in the context.\n"
    "2. After each sentence or claim, cite the passage it came from using its "
    "number in square brackets, e.g. [1] or [2].\n"
    "3. If the context does not contain enough to answer, reply with exactly: "
    "INSUFFICIENT_CONTEXT\n"
    "4. Never tell the user which choice to make or predict an outcome; explain "
    "options and the rule that applies.\n"
    "5. Be concise and plain-English. No preamble."
)


class Provider(abc.ABC):
    """Turns (question, retrieved context) into a grounded, cited answer string."""

    name: str = "base"

    @abc.abstractmethod
    def generate(self, question: str, context: List[RetrievedChunk]) -> str:
        """Return answer text with inline [n] citation markers.

        Implementations must return the sentinel ``INSUFFICIENT_CONTEXT`` if the
        context cannot support an answer.
        """
        raise NotImplementedError

    @staticmethod
    def format_context(context: List[RetrievedChunk]) -> str:
        lines = []
        for i, c in enumerate(context, start=1):
            lines.append("[{}] ({}) {}: {}".format(i, c.publisher, c.heading, c.text))
        return "\n".join(lines)
