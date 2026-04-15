#!/usr/bin/env python3
"""CLI for manual testing and administration of Marketing Automation MCP."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta

import click
from tabulate import tabulate

from src.config import Config
from src.database import DatabaseManager
from src.integrations.unified_client import Platform, UnifiedMarketingClient
from src.logger import get_logger
from src.models import (
    AnalyzeAudienceSegmentsInput,
    CreateCampaignCopyInput,
    ExecutionStatus,
    GenerateCampaignReportInput,
    MetricType,
    OptimizeCampaignBudgetInput,
    OptimizationGoal,
    ReportFormat,
    SegmentCriteria,
    ToneOfVoice,
)
from src.tools.marketing_tools import (
    analyze_audience_segments,
    create_campaign_copy,
    generate_campaign_report,
    optimize_campaign_budget,
)

logger = get_logger(__name__)


def _handle_blocked(result) -> bool:
    """Print blocked execution info and signal the caller."""
    if getattr(result, "status", None) != ExecutionStatus.BLOCKED:
        return False
    click.echo(f"⚠️  Blocked: {result.blocked_reason or 'Operation cannot proceed.'}")
    for warning in getattr(result, "warnings", []):
        click.echo(f"   - {warning}")
    return True


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Configuration file path")
@click.pass_context
def cli(ctx, config):
    """Marketing Automation MCP CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config.load(config)
    logger.info("CLI initialized", extra={"config_file": config})


@cli.command()
@click.option("--campaign-ids", "-c", multiple=True, required=True)
@click.option("--days", "-d", default=30, type=int)
@click.option(
    "--format", "-f", type=click.Choice(["json", "html", "pdf", "csv"]), default="json"
)
@click.option("--output", "-o", help="Output file path for JSON results")
def report(campaign_ids, days, format, output):
    """Generate a campaign performance report."""

    async def run():
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)
        result = await generate_campaign_report(
            GenerateCampaignReportInput(
                campaign_ids=list(campaign_ids),
                date_range={
                    "start": start_date.date().isoformat(),
                    "end": end_date.date().isoformat(),
                },
                metrics=[
                    MetricType.IMPRESSIONS,
                    MetricType.CLICKS,
                    MetricType.CONVERSIONS,
                    MetricType.COST,
                    MetricType.REVENUE,
                    MetricType.ROI,
                ],
                format=ReportFormat(format),
                include_charts=True,
            )
        )
        if _handle_blocked(result):
            return

        click.echo(f"Report ID: {result.report_id}")
        click.echo(f"Mode: {result.mode.value}")
        click.echo(f"Campaigns analyzed: {len(result.campaigns)}")
        click.echo(f"Total impressions: {result.summary['total_impressions']:,}")
        click.echo(f"Total conversions: {result.summary['total_conversions']:,}")
        click.echo(f"Average ROI: {result.summary['average_roi']:.2f}%")
        if result.warnings:
            click.echo("Warnings:")
            for warning in result.warnings:
                click.echo(f"  - {warning}")
        if output:
            with open(output, "w", encoding="utf-8") as handle:
                json.dump(result.model_dump(mode="json"), handle, indent=2)
            click.echo(f"Saved JSON report to {output}")

    asyncio.run(run())


@cli.command()
@click.option("--campaign-ids", "-c", multiple=True, required=True)
@click.option("--budget", "-b", type=float, required=True)
@click.option(
    "--goal",
    "-g",
    type=click.Choice([goal.value for goal in OptimizationGoal]),
    default=OptimizationGoal.MAXIMIZE_ROI.value,
)
@click.option("--apply", is_flag=True, help="Apply live budget changes to Google Ads")
def optimize(campaign_ids, budget, goal, apply):
    """Optimize campaign budget allocation."""

    async def run():
        result = await optimize_campaign_budget(
            OptimizeCampaignBudgetInput(
                campaign_ids=list(campaign_ids),
                total_budget=budget,
                optimization_goal=OptimizationGoal(goal),
            )
        )
        if _handle_blocked(result):
            return

        click.echo(f"Optimization ID: {result.optimization_id}")
        click.echo(f"Mode: {result.mode.value}")
        click.echo(f"Confidence score: {result.confidence_score:.2f}")
        click.echo(
            f"Projected ROI change: {result.projected_improvement.roi_change:.2f}%"
        )
        click.echo(
            f"Projected conversion change: {result.projected_improvement.conversion_change:.2f}%"
        )

        rows = [
            [
                allocation.campaign_id,
                f"${allocation.current_budget:,.2f}",
                f"${allocation.recommended_budget:,.2f}",
                f"{allocation.change_percentage:+.2f}%",
            ]
            for allocation in result.allocations
        ]
        click.echo(
            tabulate(rows, headers=["Campaign", "Current", "Recommended", "Change"])
        )

        if result.recommendations:
            click.echo("Recommendations:")
            for recommendation in result.recommendations:
                click.echo(f"  - {recommendation}")

        if apply and result.mode.value == "live":
            client = UnifiedMarketingClient()
            try:
                await client.connect(Platform.GOOGLE_ADS)
                for allocation in result.allocations:
                    await client.update_campaign_budget(
                        campaign_id=allocation.campaign_id,
                        new_budget=allocation.recommended_budget,
                    )
                    click.echo(f"Applied budget for {allocation.campaign_id}")
            finally:
                await client.disconnect_all()

    asyncio.run(run())


@cli.command()
@click.option("--product", "-p", required=True)
@click.option("--description", "-d", required=True)
@click.option("--audience", "-a", required=True)
@click.option(
    "--tone",
    "-t",
    type=click.Choice([tone.value for tone in ToneOfVoice]),
    default=ToneOfVoice.PROFESSIONAL.value,
)
@click.option("--type", "-y", "copy_type", default="ad_headline")
@click.option("--count", "-n", type=int, default=3)
def copy(product, description, audience, tone, copy_type, count):
    """Generate marketing copy."""

    async def run():
        result = await create_campaign_copy(
            CreateCampaignCopyInput(
                product_name=product,
                product_description=description,
                target_audience=audience,
                tone=ToneOfVoice(tone),
                copy_type=copy_type,
                variants_count=count,
            )
        )
        if _handle_blocked(result):
            return

        click.echo(f"Copy generation ID: {result.copy_generation_id}")
        click.echo(f"Mode: {result.mode.value}")
        for variant in result.variants:
            click.echo("")
            click.echo(f"Variant {variant.variant_id}")
            if variant.headline:
                click.echo(f"  Headline: {variant.headline}")
            click.echo(f"  Content: {variant.content}")
            if variant.call_to_action:
                click.echo(f"  CTA: {variant.call_to_action}")
            if variant.predicted_ctr is not None:
                click.echo(f"  Predicted CTR: {variant.predicted_ctr:.2f}%")
        click.echo(f"\nBest variant ID: {result.best_variant_id}")

    asyncio.run(run())


@cli.command()
@click.option("--list-id", "-l", default="main")
@click.option("--min-size", "-m", default=100, type=int)
@click.option("--max-segments", "-s", default=5, type=int)
def segment(list_id, min_size, max_segments):
    """Analyze audience segments."""

    async def run():
        result = await analyze_audience_segments(
            AnalyzeAudienceSegmentsInput(
                contact_list_id=list_id,
                criteria=[
                    SegmentCriteria.DEMOGRAPHICS,
                    SegmentCriteria.BEHAVIOR,
                    SegmentCriteria.ENGAGEMENT,
                ],
                min_segment_size=min_size,
                max_segments=max_segments,
            )
        )
        if _handle_blocked(result):
            return

        click.echo(f"Analysis ID: {result.analysis_id}")
        click.echo(f"Mode: {result.mode.value}")
        rows = [
            [
                segment.name,
                segment.size,
                segment.value_score,
                segment.engagement_score,
                json.dumps(segment.characteristics),
            ]
            for segment in result.segments
        ]
        click.echo(
            tabulate(
                rows,
                headers=["Segment", "Size", "Value", "Engagement", "Characteristics"],
            )
        )
        if result.recommendations:
            click.echo("Recommendations:")
            for recommendation in result.recommendations:
                click.echo(
                    f"  - {recommendation.segment_name}: {recommendation.strategy} via {', '.join(recommendation.channels)}"
                )

    asyncio.run(run())


@cli.command()
@click.option("--days", "-d", default=30, type=int)
def metrics(days):
    """Display automation metrics and ROI."""
    db = DatabaseManager()
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)
    roi_data = db.calculate_period_roi(period_start=start_date, period_end=end_date)
    click.echo(f"Tasks automated: {roi_data.tasks_automated}")
    click.echo(f"Time saved: {roi_data.total_time_saved_hours:.2f}h")
    click.echo(f"Labor cost saved: ${float(roi_data.labor_cost_saved):,.2f}")
    click.echo(f"ROI percentage: {roi_data.roi_percentage:.2f}%")


@cli.command()
@click.pass_context
def platforms(ctx):
    """Check platform connectivity."""

    async def run():
        client = UnifiedMarketingClient()
        config = ctx.obj["config"]
        rows = []
        for platform in Platform:
            if platform == Platform.ALL:
                continue
            if not config.has_platform_credentials(platform):
                rows.append([platform.value, "not_configured", "-"])
                continue
            try:
                await client.connect(platform)
                valid = await client.validate_credentials(platform)
                rows.append(
                    [
                        platform.value,
                        "connected" if valid.get(platform.value) else "invalid",
                        config.get_platform_config(platform.value).timeout,
                    ]
                )
            except Exception as exc:
                rows.append([platform.value, "failed", str(exc)])
        await client.disconnect_all()
        click.echo(tabulate(rows, headers=["Platform", "Status", "Detail"]))

    asyncio.run(run())


@cli.command()
@click.option("--check", "-c", is_flag=True)
@click.option("--rotate", "-r", is_flag=True)
def security(check, rotate):
    """Security management and audit."""
    from src.security import SecurityManager

    sec_mgr = SecurityManager()
    if check:
        click.echo(
            json.dumps(sec_mgr.check_environment_security(), indent=2, default=str)
        )
    if rotate:
        sec_mgr.rotate_encryption_keys()
        click.echo("Encryption keys rotated.")


@cli.command()
@click.argument("command", type=click.Choice(["start", "status"]))
def server(command):
    """Control the MCP server."""
    if command == "status":
        click.echo(
            "Server status must be checked by process supervision in this build."
        )
        return

    from src.server import main as server_main

    server_main()


if __name__ == "__main__":
    cli(obj={})
