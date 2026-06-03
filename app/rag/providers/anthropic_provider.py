"""Anthropic provider (optional). Used only when ANTHROPIC_API_KEY is set.

Falls back are handled by the factory: if the SDK or key is missing, the stub is
used instead, so the app always runs offline.
"""
from __future__ import annotations

from typing import List

from app.config import get_settings
from app.rag.providers.base import SYSTEM_CONTRACT, Provider
from app.schemas import RetrievedChunk


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self) -> None:
        import anthropic  # imported lazily; optional dependency

        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def generate(self, question: str, context: List[RetrievedChunk]) -> str:
        if not context:
            return "INSUFFICIENT_CONTEXT"
        ctx = self.format_context(context)
        user = (
            "CONTEXT:\n" + ctx + "\n\n"
            "QUESTION: " + question + "\n\n"
            "Answer using only the context, with inline [n] citations. "
            "If unsupported, reply INSUFFICIENT_CONTEXT."
        )
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=600,
            temperature=0.0,
            system=SYSTEM_CONTRACT,
            messages=[{"role": "user", "content": user}],
        )
        parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        return ("".join(parts)).strip() or "INSUFFICIENT_CONTEXT"
