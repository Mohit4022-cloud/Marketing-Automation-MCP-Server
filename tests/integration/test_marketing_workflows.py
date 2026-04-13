"""Integration coverage for demo and blocked live workflows."""

from __future__ import annotations

from click.testing import CliRunner
import pytest

from src.cli import cli


def test_demo_mode_end_to_end_tools(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    runner = CliRunner()

    report = runner.invoke(
        cli,
        ["report", "--campaign-ids", "camp_001", "--campaign-ids", "camp_002"],
    )
    optimize = runner.invoke(
        cli,
        [
            "optimize",
            "--campaign-ids",
            "camp_001",
            "--campaign-ids",
            "camp_002",
            "--budget",
            "5000",
        ],
    )
    copy = runner.invoke(
        cli,
        [
            "copy",
            "--product",
            "Marketing OS",
            "--description",
            "Turns campaign data into actions",
            "--audience",
            "Marketing leaders",
        ],
    )
    segment = runner.invoke(cli, ["segment"])

    assert report.exit_code == 0
    assert optimize.exit_code == 0
    assert copy.exit_code == 0
    assert segment.exit_code == 0
    assert "Mode: demo" in report.output
    assert "Mode: demo" in optimize.output


def test_live_mode_negative_paths(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_OPENAI_MODEL", "gpt-5.4")
    runner = CliRunner()

    report = runner.invoke(cli, ["report", "--campaign-ids", "camp_001"])
    optimize = runner.invoke(
        cli,
        ["optimize", "--campaign-ids", "camp_001", "--budget", "1000"],
    )

    assert report.exit_code == 0
    assert optimize.exit_code == 0
    assert "Blocked" in report.output
    assert "Blocked" in optimize.output
