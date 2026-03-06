"""Centralised configuration — loads .env, exposes typed settings."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "studio.db"
CACHE_DIR = BASE_DIR / "data" / "cache"
FRENCH_DATA_DIR = BASE_DIR / "data" / "french"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
FRENCH_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _require(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val


def get_optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Settings:
    OPENAI_API_KEY: str = get_optional("OPENAI_API_KEY")

    # Azure OpenAI settings
    AZURE_OPENAI_ENDPOINT: str = get_optional("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY: str = get_optional("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION: str = get_optional("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    AZURE_OPENAI_DEPLOYMENT: str = get_optional("DEPLOY", "o4-mini")

    @property
    def use_azure(self) -> bool:
        return bool(self.AZURE_OPENAI_ENDPOINT and self.AZURE_OPENAI_API_KEY)

    FRED_API_KEY: str = get_optional("FRED_API_KEY")
    SEC_EDGAR_USER_AGENT: str = get_optional(
        "SEC_EDGAR_USER_AGENT",
        "InvestmentIntelligenceStudio/1.0 (admin@example.com)",
    )
    LLM_MODEL: str = get_optional("LLM_MODEL", "gpt-4o")
    LLM_TEMPERATURE: float = float(get_optional("LLM_TEMPERATURE", "0.2"))

    FRED_RATE_LIMIT_PER_MIN: int = 120
    SEC_RATE_LIMIT_PER_SEC: int = 10

    CACHE_TTL_SECONDS: int = 3600


settings = Settings()
