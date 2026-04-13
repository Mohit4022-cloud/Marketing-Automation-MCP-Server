"""Unit tests for MCP tool contracts and execution modes."""

from __future__ import annotations

from src.models import (
    AnalyzeAudienceSegmentsInput,
    CreateCampaignCopyInput,
    ExecutionMode,
    ExecutionStatus,
    GenerateCampaignReportInput,
    MetricType,
    OptimizeCampaignBudgetInput,
    OptimizationGoal,
    SegmentCriteria,
    ToneOfVoice,
)
from src.tools.marketing_tools import (
    analyze_audience_segments,
    create_campaign_copy,
    generate_campaign_report,
    optimize_campaign_budget,
)


def test_demo_report_is_deterministic(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    input_data = GenerateCampaignReportInput(
        campaign_ids=["camp_001", "camp_002"],
        date_range={"start": "2024-01-01", "end": "2024-01-31"},
        metrics=[MetricType.IMPRESSIONS, MetricType.CLICKS, MetricType.CONVERSIONS],
    )
    first = __import__("asyncio").run(generate_campaign_report(input_data))
    second = __import__("asyncio").run(generate_campaign_report(input_data))
    assert first.mode == ExecutionMode.DEMO
    assert first.summary == second.summary
    assert [campaign.model_dump() for campaign in first.campaigns] == [
        campaign.model_dump() for campaign in second.campaigns
    ]


def test_live_report_blocks_without_platform_credentials(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_OPENAI_MODEL", "gpt-5.4")
    result = __import__("asyncio").run(
        generate_campaign_report(
            GenerateCampaignReportInput(
                campaign_ids=["camp_001"],
                date_range={"start": "2024-01-01", "end": "2024-01-31"},
                metrics=[MetricType.IMPRESSIONS],
            )
        )
    )
    assert result.status == ExecutionStatus.BLOCKED
    assert result.mode == ExecutionMode.LIVE


def test_live_copy_blocks_without_provider_credentials(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AI_OPENAI_MODEL", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    result = __import__("asyncio").run(
        create_campaign_copy(
            CreateCampaignCopyInput(
                product_name="Offer",
                product_description="Description",
                target_audience="Marketing leaders",
                tone=ToneOfVoice.PROFESSIONAL,
                copy_type="ad_headline",
            )
        )
    )
    assert result.status == ExecutionStatus.BLOCKED
    assert "provider" in result.blocked_reason.lower()


def test_demo_segments_return_structured_recommendations(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    result = __import__("asyncio").run(
        analyze_audience_segments(
            AnalyzeAudienceSegmentsInput(
                contact_list_id="list_001",
                criteria=[SegmentCriteria.DEMOGRAPHICS, SegmentCriteria.BEHAVIOR],
                min_segment_size=50,
                max_segments=3,
            )
        )
    )
    assert result.status == ExecutionStatus.OK
    assert result.mode == ExecutionMode.DEMO
    assert result.recommendations
    assert result.recommendations[0].segment_name


def test_demo_optimization_returns_allocations(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    result = __import__("asyncio").run(
        optimize_campaign_budget(
            OptimizeCampaignBudgetInput(
                campaign_ids=["camp_001", "camp_002"],
                total_budget=5000,
                optimization_goal=OptimizationGoal.MAXIMIZE_ROI,
            )
        )
    )
    assert result.status == ExecutionStatus.OK
    assert result.mode == ExecutionMode.DEMO
    assert len(result.allocations) == 2
