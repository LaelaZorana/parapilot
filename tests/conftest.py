"""Shared pytest fixtures."""
from __future__ import annotations

import os

import pytest

# Force the deterministic offline stub for all tests, regardless of env.
os.environ["PARAPILOT_PROVIDER"] = "stub"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)


@pytest.fixture(scope="session")
def retriever():
    from app.rag.retriever import get_retriever

    return get_retriever()


@pytest.fixture(scope="session")
def engine():
    from app.process.engine import get_engine

    return get_engine()
