"""Shared dependencies / singletons for the web layer."""
from __future__ import annotations

from app.process.engine import ProcessEngine, get_engine
from app.rag.providers import get_provider
from app.rag.retriever import Retriever, get_retriever

__all__ = ["get_engine", "get_retriever", "get_provider", "ProcessEngine", "Retriever"]
