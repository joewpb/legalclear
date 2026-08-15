"""S3-3: missing required config (Supabase/Anthropic creds) must raise loudly
outside local dev, instead of silently degrading to an empty product."""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def _reload_config():
    from src.core import config

    return importlib.reload(config)


def test_missing_required_config_raises_outside_development(monkeypatch):
    config = _reload_config()
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config.settings, "SUPABASE_URL", "")
    monkeypatch.setattr(config.settings, "SUPABASE_SERVICE_KEY", "set")
    monkeypatch.setattr(config.settings, "ANTHROPIC_API_KEY", "set")

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        config.validate_startup_config()


def test_missing_required_config_does_not_raise_in_development(monkeypatch):
    config = _reload_config()
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(config.settings, "SUPABASE_URL", "")
    monkeypatch.setattr(config.settings, "SUPABASE_SERVICE_KEY", "")
    monkeypatch.setattr(config.settings, "ANTHROPIC_API_KEY", "")

    config.validate_startup_config()  # must not raise


def test_complete_config_does_not_raise_outside_development(monkeypatch):
    config = _reload_config()
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config.settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(config.settings, "SUPABASE_SERVICE_KEY", "set")
    monkeypatch.setattr(config.settings, "ANTHROPIC_API_KEY", "set")

    config.validate_startup_config()  # must not raise
