"""Marketing Automation MCP server."""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .models import (
    AnalyzeAudienceSegmentsInput,
    AnalyzeAudienceSegmentsOutput,
    CreateCampaignCopyInput,
    CreateCampaignCopyOutput,
    GenerateCampaignReportInput,
    GenerateCampaignReportOutput,
    MetricType,
    OptimizeCampaignBudgetInput,
    OptimizeCampaignBudgetOutput,
    OptimizationGoal,
    ReportFormat,
    SegmentCriteria,
    ToneOfVoice,
)
from .tools.marketing_tools import (
    analyze_audience_segments as analyze_audience_segments_impl,
    create_campaign_copy as create_campaign_copy_impl,
    generate_campaign_report as generate_campaign_report_impl,
    optimize_campaign_budget as optimize_campaign_budget_impl,
)

SERVER_INSTRUCTIONS = (
    "Marketing Automation MCP exposes deterministic demo workflows and honest live-mode "
    "blocked responses. The supported transport for this repo is stdio."
)

mcp = FastMCP(
    "marketing-automation",
    instructions=SERVER_INSTRUCTIONS,
    json_response=True,
    log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
)


@mcp.tool(
    name="generate_campaign_report",
    description="Generate campaign performance reports using live platform data or deterministic demo mode.",
)
async def generate_campaign_report(
    campaign_ids: list[str],
    date_range: dict[str, str],
    metrics: list[MetricType],
    format: ReportFormat = ReportFormat.JSON,
    include_charts: bool = True,
    group_by: str | None = "campaign",
) -> GenerateCampaignReportOutput:
    """Run the report tool with the canonical input schema."""
    return await generate_campaign_report_impl(
        GenerateCampaignReportInput(
            campaign_ids=campaign_ids,
            date_range=date_range,
            metrics=metrics,
            format=format,
            include_charts=include_charts,
            group_by=group_by,
        )
    )


@mcp.tool(
    name="optimize_campaign_budget",
    description="Reallocate campaign budget using live platform metrics and provider-backed optimization logic.",
)
async def optimize_campaign_budget(
    campaign_ids: list[str],
    total_budget: float,
    optimization_goal: OptimizationGoal = OptimizationGoal.MAXIMIZE_ROI,
    constraints: dict[str, Any] | None = None,
    historical_days: int = 30,
    include_projections: bool = True,
) -> OptimizeCampaignBudgetOutput:
    """Run the optimization tool with the canonical input schema."""
    return await optimize_campaign_budget_impl(
        OptimizeCampaignBudgetInput(
            campaign_ids=campaign_ids,
            total_budget=total_budget,
            optimization_goal=optimization_goal,
            constraints=constraints or {},
            historical_days=historical_days,
            include_projections=include_projections,
        )
    )


@mcp.tool(
    name="create_campaign_copy",
    description="Generate campaign copy variants through the configured AI provider or deterministic demo mode.",
)
async def create_campaign_copy(
    product_name: str,
    product_description: str,
    target_audience: str,
    tone: ToneOfVoice,
    copy_type: str,
    variants_count: int = 3,
    keywords: list[str] | None = None,
    max_length: int | None = None,
    call_to_action: str | None = None,
) -> CreateCampaignCopyOutput:
    """Run the copy tool with the canonical input schema."""
    return await create_campaign_copy_impl(
        CreateCampaignCopyInput(
            product_name=product_name,
            product_description=product_description,
            target_audience=target_audience,
            tone=tone,
            copy_type=copy_type,
            variants_count=variants_count,
            keywords=keywords or [],
            max_length=max_length,
            call_to_action=call_to_action,
        )
    )


@mcp.tool(
    name="analyze_audience_segments",
    description="Analyze audience segments in deterministic demo mode or return a structured live-mode block.",
)
async def analyze_audience_segments(
    contact_list_id: str,
    criteria: list[SegmentCriteria],
    min_segment_size: int = 100,
    max_segments: int = 10,
    include_recommendations: bool = True,
    analyze_overlap: bool = True,
) -> AnalyzeAudienceSegmentsOutput:
    """Run the audience tool with the canonical input schema."""
    return await analyze_audience_segments_impl(
        AnalyzeAudienceSegmentsInput(
            contact_list_id=contact_list_id,
            criteria=criteria,
            min_segment_size=min_segment_size,
            max_segments=max_segments,
            include_recommendations=include_recommendations,
            analyze_overlap=analyze_overlap,
        )
    )


def main() -> None:
    """Run the MCP server in its supported transport mode."""
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    if transport != "stdio":
        raise ValueError(
            "This repo currently documents and supports stdio transport only. "
            "Set MCP_TRANSPORT=stdio or remove the override."
        )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
