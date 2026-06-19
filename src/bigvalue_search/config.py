"""Configuration module for BigValue search tool."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root (walk up from this file)
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)


class Config:
    """Application configuration from environment variables."""

    # BigValue credentials
    BIGVALUE_EMAIL: str = os.getenv("BIGVALUE_EMAIL", "")
    BIGVALUE_PASSWORD: str = os.getenv("BIGVALUE_PASSWORD", "")
    BIGVALUE_API_BASE: str = os.getenv("BIGVALUE_API_BASE", "https://service.bigvalue.ai")
    BIGVALUE_API_URL: str = os.getenv("BIGVALUE_API_URL", "https://api.bigvalue.co.kr")

    # Playwright settings
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "30000"))

    # Geocoding
    NOMINATIM_USER_AGENT: str = "bigvalue-search-tool/1.0"

    # Search defaults
    DEFAULT_RADIUS_M: int = 50
    GRID_INTERVAL_M: int = 8  # meters between grid points

    # Output
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required config. Returns list of missing fields."""
        errors: list[str] = []
        if not cls.BIGVALUE_EMAIL:
            errors.append("BIGVALUE_EMAIL is not set")
        if not cls.BIGVALUE_PASSWORD:
            errors.append("BIGVALUE_PASSWORD is not set")
        return errors


config = Config()
