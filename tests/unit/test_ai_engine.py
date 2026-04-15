"""Unit tests for provider-backed AI engine behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.ai.providers import BaseAIProvider, ProviderRegistry
from src.ai_engine import MarketingAIEngine


class FakeProvider(BaseAIProvider):
    """Minimal provider for deterministic AI engine tests."""

    name = "fake"

    def __init__(self, payloads):
        super().__init__(api_key="test", model="fake-model")
        self.payloads = list(payloads)

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        payload = self.payloads.pop(0)
        return payload if isinstance(payload, str) else ""

    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str, schema
    ):
        return self.payloads.pop(0)


def test_provider_registry_defaults_to_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = ProviderRegistry().get_provider()
    assert provider.name == "openai"
    assert provider.model == "gpt-5.4"


def test_provider_registry_can_select_anthropic(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")
    provider = ProviderRegistry().get_provider()
    assert provider.name == "anthropic"
    assert provider.model == "claude-test"


@pytest.mark.asyncio
async def test_analyze_campaign_performance_uses_provider():
    provider = FakeProvider(
        [
            {
                "campaigns": [
                    {
                        "campaign_id": "camp_001",
                        "campaign_name": "Summer Sale",
                        "impressions": 10000,
                        "clicks": 250,
                        "conversions": 18,
                        "cost": 500.0,
                        "revenue": 1800.0,
                        "ctr": 2.5,
                        "conversion_rate": 7.2,
                        "roi": 260.0,
                        "trend": "improving",
                    }
                ]
            }
        ]
    )
    engine = MarketingAIEngine(provider=provider)
    result = await engine.analyze_campaign_performance(
        campaigns=[
            {
                "campaign_id": "camp_001",
                "campaign_name": "Summer Sale",
                "metrics": {
                    "impressions": 10000,
                    "clicks": 250,
                    "conversions": 18,
                    "cost": 500.0,
                    "revenue": 1800.0,
                },
            }
        ],
        start_date=datetime.now(UTC) - timedelta(days=7),
        end_date=datetime.now(UTC),
    )
    assert len(result) == 1
    assert result[0].trend == "improving"
    assert result[0].roi == 260.0


@pytest.mark.asyncio
async def test_create_budget_reallocation_chain_returns_step_results():
    provider = FakeProvider(
        [
            {
                "campaigns": [
                    {
                        "campaign_id": "camp_001",
                        "campaign_name": "Summer Sale",
                        "impressions": 10000,
                        "clicks": 250,
                        "conversions": 18,
                        "cost": 500.0,
                        "revenue": 1800.0,
                        "ctr": 2.5,
                        "conversion_rate": 7.2,
                        "roi": 260.0,
                        "trend": "improving",
                    }
                ]
            },
            {"trend_summary": "Momentum is positive", "risk_factors": ["competition"]},
            {
                "suggestions": [
                    {
                        "type": "budget_reallocation",
                        "campaign_id": "camp_001",
                        "action": "Increase budget 15%",
                        "predicted_impact": {
                            "roi_change": 12.0,
                            "conversion_change": 8.0,
                            "cost_change": 15.0,
                        },
                        "confidence": 0.86,
                        "reasoning": "Best recent ROI trend",
                        "implementation_steps": ["Increase daily budget"],
                    }
                ]
            },
        ]
    )
    engine = MarketingAIEngine(provider=provider)
    result = await engine.create_budget_reallocation_chain(
        campaigns=[
            {
                "campaign_id": "camp_001",
                "campaign_name": "Summer Sale",
                "metrics": {
                    "clicks": 250,
                    "conversions": 18,
                    "cost": 500,
                    "revenue": 1800,
                },
            }
        ],
        total_budget=5000,
        business_goals={"primary_goal": "maximize_roi"},
    )
    assert result["chain_name"] == "budget_reallocation"
    assert [step["step_name"] for step in result["steps"]] == [
        "performance_analysis",
        "trend_prediction",
        "optimization",
    ]
