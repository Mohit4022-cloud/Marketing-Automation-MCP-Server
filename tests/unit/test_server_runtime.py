"""Tests for MCP server runtime decisions."""

from __future__ import annotations

import pytest

from src import server


def test_server_exposes_marketing_automation_fastmcp_instance():
    assert server.mcp.name == "marketing-automation"


def test_server_rejects_non_stdio_transport(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")

    with pytest.raises(ValueError, match="stdio"):
        server.main()
