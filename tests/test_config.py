"""Tests for environment-driven configuration validation."""

import sys

sys.path.insert(0, "src")

import pytest

from discount_nepal.config import Config


class TestConfig:
    def test_defaults_are_sane(self):
        config = Config()
        assert config.port == 8000
        assert config.cache_ttl_seconds >= 0
        assert config.request_timeout >= 1
        assert config.max_retries >= 0
        assert config.concurrent_workers >= 1

    def test_invalid_port_rejected(self):
        with pytest.raises(ValueError, match="Invalid port"):
            Config(port=0)
        with pytest.raises(ValueError, match="Invalid port"):
            Config(port=70000)

    def test_negative_ttl_rejected(self):
        with pytest.raises(ValueError, match="cache_ttl_seconds"):
            Config(cache_ttl_seconds=-1)

    def test_zero_timeout_rejected(self):
        with pytest.raises(ValueError, match="request_timeout"):
            Config(request_timeout=0)

    def test_environment_overrides(self, monkeypatch):
        monkeypatch.setenv("DISCOUNT_NEPAL_PORT", "9001")
        monkeypatch.setenv("DISCOUNT_NEPAL_CACHE_TTL", "300")
        # Config reads env at class-definition time, so re-exec the module
        # logic by constructing from the same env-driven defaults.
        import importlib

        from discount_nepal import config as config_module

        importlib.reload(config_module)
        assert config_module.config.port == 9001
        assert config_module.config.cache_ttl_seconds == 300
