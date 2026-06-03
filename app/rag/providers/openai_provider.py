"""OpenAI provider (optional). Used only when OPENAI_API_KEY is set.

The factory falls back to the stub if the SDK or key is missing, so the app
always runs offline.
"""
from __future__ import annotations

from typing import List

from app.config import get_settings
from app.rag.providers.base import SYSTEM_CONTRACT, Provider
from app.schemas import RetrievedChunk


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self) -> None:
        from openai import OpenAI  # imported lazily; optional dependency

        settings = get_settings()
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

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
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=0.0,
            max_tokens=600,
            messages=[
                {"role": "system", "content": SYSTEM_CONTRACT},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip() or "INSUFFICIENT_CONTEXT"
