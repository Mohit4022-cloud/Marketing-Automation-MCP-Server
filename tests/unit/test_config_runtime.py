"""Tests for runtime and security-related configuration behavior."""

from __future__ import annotations

import pytest

from src.config import Config
from src.security import SecurityManager


def test_missing_encryption_key_disables_value_encryption(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    config = Config.load()

    assert config.security.api_key_encryption is False
    assert config.encrypt_value("secret-value") == "secret-value"
    assert config.decrypt_value("secret-value") == "secret-value"


def test_session_tokens_require_explicit_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        SecurityManager().generate_session_token("user-123")
