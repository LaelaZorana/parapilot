"""LLM provider interface + factory.

Default is the deterministic offline STUB. Anthropic/OpenAI are used only when a
key is configured, and each falls back to the stub if its SDK or key is missing,
so the app always works offline.
"""
from __future__ import annotations

from app.config import get_settings
from app.rag.providers.base import Provider
from app.rag.providers.stub import StubProvider


def get_provider() -> Provider:
    settings = get_settings()
    choice = (settings.provider or "stub").lower()

    if choice == "anthropic" and settings.anthropic_api_key:
        try:
            from app.rag.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider()
        except Exception:
            return StubProvider()

    if choice == "openai" and settings.openai_api_key:
        try:
            from app.rag.providers.openai_provider import OpenAIProvider

            return OpenAIProvider()
        except Exception:
            return StubProvider()

    return StubProvider()
