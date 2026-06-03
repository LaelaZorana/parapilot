"""Application configuration.

Everything has a safe offline default. With no environment at all, ParaPilot
runs fully offline on the deterministic stub provider.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root (…/parapilot). config.py lives in app/, so parents[1].
ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime settings, overridable via environment / .env."""

    model_config = SettingsConfigDict(
        env_prefix="PARAPILOT_",
        env_file=".env",
        extra="ignore",
    )

    # Provider: "stub" (default, offline), "anthropic", or "openai".
    provider: str = "stub"
    anthropic_model: str = "claude-3-5-haiku-latest"
    openai_model: str = "gpt-4o-mini"

    # Retrieval / generation.
    confidence_threshold: float = 0.12
    top_k: int = 4

    # Storage.
    db_url: str = "sqlite:///./parapilot.db"
    corpus_dir: str = "data/corpus"

    # Optional case law (off by default).
    enable_caselaw: bool = False

    @property
    def corpus_path(self) -> Path:
        p = Path(self.corpus_dir)
        return p if p.is_absolute() else ROOT_DIR / p

    @property
    def anthropic_api_key(self) -> Optional[str]:
        import os

        return os.getenv("ANTHROPIC_API_KEY")

    @property
    def openai_api_key(self) -> Optional[str]:
        import os

        return os.getenv("OPENAI_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
