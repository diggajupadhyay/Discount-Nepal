"""Shared configuration for Discount Nepal."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Runtime configuration. All values can be overridden via environment variables."""

    host: str = os.getenv("DISCOUNT_NEPAL_HOST", "127.0.0.1")
    port: int = int(os.getenv("DISCOUNT_NEPAL_PORT", "8000"))
    cache_ttl_seconds: int = int(os.getenv("DISCOUNT_NEPAL_CACHE_TTL", "120"))
    request_timeout: int = int(os.getenv("DISCOUNT_NEPAL_TIMEOUT", "20"))
    max_retries: int = int(os.getenv("DISCOUNT_NEPAL_MAX_RETRIES", "2"))
    user_agent: str = os.getenv(
        "DISCOUNT_NEPAL_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
    )
    concurrent_workers: int = int(os.getenv("DISCOUNT_NEPAL_WORKERS", "8"))

    def __post_init__(self) -> None:
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")
        if self.cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds must be >= 0")
        if self.request_timeout < 1:
            raise ValueError("request_timeout must be >= 1")


config = Config()
