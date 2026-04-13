"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import set_config


@pytest.fixture(autouse=True)
def reset_global_config(monkeypatch):
    """Reset cached config and isolate database path for each test."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    set_config(None)
    yield
    set_config(None)
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def mock_google_ads_client():
    """Mock Google Ads HTTP client."""
    with patch("src.integrations.base.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = Mock(
            status_code=200,
            json=lambda: {"access_token": "mock_token", "expires_in": 3600},
            text="ok",
        )
        mock_instance.request.return_value = Mock(
            status_code=200,
            json=lambda: {
                "results": [
                    {
                        "campaign": {
                            "id": "123456",
                            "name": "Test Campaign",
                            "status": "ENABLED",
                        },
                        "segments": {"date": "2024-01-01"},
                        "metrics": {
                            "impressions": 10000,
                            "clicks": 200,
                            "conversions": 10,
                            "cost_micros": 500000000,
                        },
                    }
                ]
            },
            text="ok",
        )
        mock_client.return_value = mock_instance
        yield mock_instance
