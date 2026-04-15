"""Marketing automation MCP tools with explicit demo/live execution paths."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
import hashlib
import random
import uuid
from typing import Dict, Iterable, List, Sequence, Tuple

from ..ai.providers import AIProviderNotConfiguredError
from ..ai_engine import MarketingAIEngine
from ..config import get_config
from ..database import Campaign, DatabaseManager, DecisionType, PerformanceMetrics
from ..integrations.unified_client import Platform, UnifiedMarketingClient
from ..models import (
    AnalyzeAudienceSegmentsInput,
    AnalyzeAudienceSegmentsOutput,
    AudienceRecommendation,
    AudienceSegment,
    BudgetAllocation,
    CampaignMetrics,
    CopyVariant,
    CreateCampaignCopyInput,
    CreateCampaignCopyOutput,
    ExecutionMode,
    ExecutionStatus,
    GenerateCampaignReportInput,
    GenerateCampaignReportOutput,
    MetricType,
    OptimizeCampaignBudgetInput,
    OptimizeCampaignBudgetOutput,
    OptimizationGoal,
    ProjectedImprovement,
    ReportFormat,
    SegmentOverlap,
)


def _stable_id(*parts: str) -> str:
    """Create a deterministic UUID string from input parts."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "::".join(parts)))


def _stable_random(*parts: str) -> random.Random:
    """Create a deterministic random generator."""
    seed_material = "::".join(parts).encode("utf-8")
    seed = int(hashlib.sha256(seed_material).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _utcnow() -> datetime:
    """Return an aware UTC timestamp for runtime use."""
    return datetime.now(UTC)


def _mode_from_config() -> ExecutionMode:
    return ExecutionMode.DEMO if get_config().ai.demo_mode else ExecutionMode.LIVE


def _zero_report_summary() -> Dict[str, float]:
    return {
        "total_impressions": 0,
        "total_clicks": 0,
        "total_conversions": 0,
        "total_cost": 0.0,
        "total_revenue": 0.0,
        "average_ctr": 0.0,
        "average_conversion_rate": 0.0,
        "average_roi": 0.0,
    }


def _blocked_report(
    input_data: GenerateCampaignReportInput,
    reason: str,
    warnings: List[str] | None = None,
) -> GenerateCampaignReportOutput:
    return GenerateCampaignReportOutput(
        status=ExecutionStatus.BLOCKED,
        mode=ExecutionMode.LIVE,
        blocked_reason=reason,
        warnings=warnings or [],
        report_id=str(uuid.uuid4()),
        generated_at=_utcnow(),
        date_range=input_data.date_range,
        campaigns=[],
        summary=_zero_report_summary(),
        charts=None,
        format=input_data.format,
        download_url=None,
    )


def _blocked_optimization(
    input_data: OptimizeCampaignBudgetInput,
    reason: str,
    warnings: List[str] | None = None,
) -> OptimizeCampaignBudgetOutput:
    return OptimizeCampaignBudgetOutput(
        status=ExecutionStatus.BLOCKED,
        mode=ExecutionMode.LIVE,
        blocked_reason=reason,
        warnings=warnings or [],
        optimization_id=str(uuid.uuid4()),
        total_budget=input_data.total_budget,
        optimization_goal=input_data.optimization_goal,
        allocations=[],
        projected_improvement=ProjectedImprovement(),
        confidence_score=0.0,
        recommendations=[],
    )


def _blocked_copy(
    input_data: CreateCampaignCopyInput,
    reason: str,
    warnings: List[str] | None = None,
) -> CreateCampaignCopyOutput:
    return CreateCampaignCopyOutput(
        status=ExecutionStatus.BLOCKED,
        mode=ExecutionMode.LIVE,
        blocked_reason=reason,
        warnings=warnings or [],
        copy_generation_id=str(uuid.uuid4()),
        copy_type=input_data.copy_type,
        variants=[],
        tone=input_data.tone,
        target_audience=input_data.target_audience,
        keywords_used=input_data.keywords,
        best_variant_id=None,
        generation_metadata={},
    )


def _blocked_segments(
    input_data: AnalyzeAudienceSegmentsInput,
    reason: str,
    warnings: List[str] | None = None,
) -> AnalyzeAudienceSegmentsOutput:
    return AnalyzeAudienceSegmentsOutput(
        status=ExecutionStatus.BLOCKED,
        mode=ExecutionMode.LIVE,
        blocked_reason=reason,
        warnings=warnings or [],
        analysis_id=str(uuid.uuid4()),
        total_contacts=0,
        segments=[],
        uncategorized_count=0,
        overlaps=None,
        recommendations=[],
        insights=[],
        created_at=_utcnow(),
    )


async def _connect_available_platforms() -> (
    Tuple[UnifiedMarketingClient, List[Platform], List[str]]
):
    """Connect to all configured platforms and collect warnings for failures."""
    config = get_config()
    client = UnifiedMarketingClient()
    connected: List[Platform] = []
    warnings: List[str] = []

    for platform in (
        Platform.GOOGLE_ADS,
        Platform.FACEBOOK_ADS,
        Platform.GOOGLE_ANALYTICS,
    ):
        if not config.has_platform_credentials(platform):
            continue
        try:
            await client.connect(platform)
            connected.append(platform)
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via integration boundaries
            warnings.append(f"Failed to connect to {platform.value}: {exc}")

    return client, connected, warnings


def _derive_metrics(raw: Dict[str, float]) -> Dict[str, float]:
    """Derive campaign rates from raw metrics."""
    impressions = int(raw.get("impressions", 0))
    clicks = int(raw.get("clicks", 0))
    conversions = int(raw.get("conversions", 0))
    cost = float(raw.get("cost", 0.0))
    revenue = float(raw.get("revenue", 0.0))
    ctr = (clicks / impressions * 100) if impressions else 0.0
    conversion_rate = (conversions / clicks * 100) if clicks else 0.0
    roi = ((revenue - cost) / cost * 100) if cost else 0.0
    return {
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "cost": round(cost, 2),
        "revenue": round(revenue, 2),
        "ctr": round(ctr, 2),
        "conversion_rate": round(conversion_rate, 2),
        "roi": round(roi, 2),
        "reach": round(float(raw.get("reach", 0.0)), 2) if raw.get("reach") else None,
    }


def _aggregate_campaign_rows(results: Dict[str, Dict]) -> List[CampaignMetrics]:
    """Aggregate platform rows into canonical campaign metrics."""
    aggregated: Dict[str, Dict[str, float | str | set]] = {}
    for platform_name, payload in results.items():
        for row in payload.get("data", []):
            campaign_id = str(row["campaign_id"])
            if campaign_id not in aggregated:
                aggregated[campaign_id] = {
                    "campaign_name": row.get("campaign_name") or campaign_id,
                    "platforms": set(),
                    "impressions": 0.0,
                    "clicks": 0.0,
                    "conversions": 0.0,
                    "cost": 0.0,
                    "revenue": 0.0,
                    "reach": 0.0,
                }
            entry = aggregated[campaign_id]
            entry["platforms"].add(platform_name)
            for metric_name, metric_value in row.get("metrics", {}).items():
                if metric_name in {
                    "impressions",
                    "clicks",
                    "conversions",
                    "cost",
                    "revenue",
                    "reach",
                }:
                    entry[metric_name] += float(metric_value or 0.0)

    campaigns: List[CampaignMetrics] = []
    for campaign_id, entry in aggregated.items():
        derived = _derive_metrics(entry)
        platforms = sorted(entry["platforms"])
        campaigns.append(
            CampaignMetrics(
                campaign_id=campaign_id,
                campaign_name=str(entry["campaign_name"]),
                platform=(
                    "multi"
                    if len(platforms) > 1
                    else (platforms[0] if platforms else None)
                ),
                **derived,
            )
        )
    return sorted(campaigns, key=lambda campaign: campaign.campaign_id)


def _build_report_summary(campaigns: Sequence[CampaignMetrics]) -> Dict[str, float]:
    """Build canonical report summary fields."""
    if not campaigns:
        return _zero_report_summary()
    return {
        "total_impressions": sum(campaign.impressions for campaign in campaigns),
        "total_clicks": sum(campaign.clicks for campaign in campaigns),
        "total_conversions": sum(campaign.conversions for campaign in campaigns),
        "total_cost": round(sum(campaign.cost for campaign in campaigns), 2),
        "total_revenue": round(sum(campaign.revenue for campaign in campaigns), 2),
        "average_ctr": round(
            sum(campaign.ctr for campaign in campaigns) / len(campaigns), 2
        ),
        "average_conversion_rate": round(
            sum(campaign.conversion_rate for campaign in campaigns) / len(campaigns), 2
        ),
        "average_roi": round(
            sum(campaign.roi for campaign in campaigns) / len(campaigns), 2
        ),
    }


def _build_report_charts(
    campaigns: Sequence[CampaignMetrics],
) -> List[Dict[str, object]]:
    """Build lightweight chart descriptors for report consumers."""
    return [
        {
            "type": "bar",
            "title": "ROI by Campaign",
            "data": {
                "labels": [campaign.campaign_name for campaign in campaigns],
                "values": [campaign.roi for campaign in campaigns],
            },
        },
        {
            "type": "bar",
            "title": "Conversions by Campaign",
            "data": {
                "labels": [campaign.campaign_name for campaign in campaigns],
                "values": [campaign.conversions for campaign in campaigns],
            },
        },
    ]


def _persist_campaign_snapshots(
    campaigns: Sequence[CampaignMetrics], window_start: str, window_end: str
):
    """Persist live campaign snapshots into the database layer idempotently."""
    if not campaigns:
        return
    db = DatabaseManager()
    with db.get_session() as session:
        for campaign in campaigns:
            existing = (
                session.query(Campaign)
                .filter_by(campaign_id=campaign.campaign_id)
                .first()
            )
            if not existing:
                existing = Campaign(
                    campaign_id=campaign.campaign_id,
                    name=campaign.campaign_name,
                    platform=campaign.platform or "aggregated",
                    status="active",
                    budget=0,
                    start_date=_utcnow() - timedelta(days=30),
                )
                session.add(existing)
                session.flush()
            metric_id = _stable_id(
                "metric", campaign.campaign_id, window_start, window_end
            )
            metric = (
                session.query(PerformanceMetrics).filter_by(metric_id=metric_id).first()
            )
            if not metric:
                metric = PerformanceMetrics(
                    metric_id=metric_id,
                    campaign_id=existing.id,
                    metric_date=_utcnow(),
                )
                session.add(metric)
            metric.impressions = campaign.impressions
            metric.clicks = campaign.clicks
            metric.conversions = campaign.conversions
            metric.revenue = campaign.revenue
            metric.cost = campaign.cost
            metric.ctr = campaign.ctr
            metric.conversion_rate = campaign.conversion_rate
            metric.roas = (campaign.revenue / campaign.cost) if campaign.cost else 0
            metric.is_automated = False
            metric.automation_applied = ["mcp_report_sync"]


def _demo_campaign_metrics(
    input_data: GenerateCampaignReportInput,
) -> List[CampaignMetrics]:
    """Generate deterministic demo report data."""
    campaigns: List[CampaignMetrics] = []
    for campaign_id in input_data.campaign_ids:
        rng = _stable_random(
            "report",
            campaign_id,
            input_data.date_range["start"],
            input_data.date_range["end"],
        )
        impressions = rng.randint(12_000, 90_000)
        clicks = int(impressions * rng.uniform(0.015, 0.06))
        conversions = int(clicks * rng.uniform(0.02, 0.12))
        cost = round(clicks * rng.uniform(1.5, 4.0), 2)
        revenue = round(conversions * rng.uniform(80, 320), 2)
        campaigns.append(
            CampaignMetrics(
                campaign_id=campaign_id,
                campaign_name=f"Campaign {campaign_id[-6:]}",
                platform="demo",
                **_derive_metrics(
                    {
                        "impressions": impressions,
                        "clicks": clicks,
                        "conversions": conversions,
                        "cost": cost,
                        "revenue": revenue,
                        "reach": impressions * rng.uniform(0.7, 0.92),
                    }
                ),
            )
        )
    return campaigns


def _build_demo_copy_variant(
    input_data: CreateCampaignCopyInput, index: int
) -> CopyVariant:
    """Generate a deterministic copy variant for demo mode."""
    rng = _stable_random(
        "copy",
        input_data.product_name,
        input_data.target_audience,
        input_data.copy_type,
        str(index),
    )
    benefits = [
        "cut manual campaign work",
        "surface the highest-value optimizations",
        "turn performance data into action faster",
    ]
    verbs = ["Unlock", "Scale", "Improve", "Reduce"]
    cta = (
        input_data.call_to_action
        or ["Book a demo", "See the workflow", "Get started"][index % 3]
    )
    headline = f"{rng.choice(verbs)} {input_data.product_name}"
    content = (
        f"{headline}: {input_data.product_description}. "
        f"For {input_data.target_audience}, this helps {rng.choice(benefits)}. {cta}."
    )
    if input_data.keywords:
        content = f"{content} {' '.join(input_data.keywords[:2])}"
    if input_data.max_length and len(content) > input_data.max_length:
        content = f"{content[: input_data.max_length - 3]}..."
    return CopyVariant(
        variant_id=_stable_id("copy", input_data.product_name, str(index)),
        content=content,
        tone_match_score=round(0.86 + (index * 0.03), 2),
        predicted_ctr=round(2.4 + index * 0.6, 2),
        keywords=input_data.keywords[:],
        key_elements=[
            input_data.product_name,
            input_data.target_audience,
            input_data.tone.value,
        ],
        character_count=len(content),
        word_count=len(content.split()),
        headline=headline,
        call_to_action=cta,
    )


def _demo_segments(
    input_data: AnalyzeAudienceSegmentsInput,
) -> Tuple[List[AudienceSegment], List[SegmentOverlap], List[AudienceRecommendation]]:
    """Generate deterministic audience segments for demo mode."""
    criteria_labels = [criterion.value for criterion in input_data.criteria]
    rng = _stable_random("segments", input_data.contact_list_id, *criteria_labels)
    templates = [
        ("High-Intent Buyers", {"engagement": "high", "purchase_history": "recent"}),
        (
            "Expansion Accounts",
            {"company_size": "mid-market", "interest": "automation"},
        ),
        ("Reactivation Targets", {"recency": "90+ days", "engagement": "declining"}),
        ("Exec Champions", {"title_band": "director+", "seniority": "high"}),
    ]
    segments: List[AudienceSegment] = []
    overlaps: List[SegmentOverlap] = []
    recommendations: List[AudienceRecommendation] = []
    max_segments = min(input_data.max_segments, len(templates))
    for index in range(max_segments):
        name, characteristics = templates[index]
        size = input_data.min_segment_size + rng.randint(0, 300)
        segment_id = _stable_id("segment", input_data.contact_list_id, name)
        segments.append(
            AudienceSegment(
                segment_id=segment_id,
                name=name,
                size=size,
                criteria={criterion.value: True for criterion in input_data.criteria},
                characteristics=characteristics,
                engagement_score=round(0.55 + index * 0.08, 2),
                value_score=round(0.62 + index * 0.07, 2),
                recommended_campaigns=[
                    "Budget Reallocation",
                    "Creative Refresh",
                    "Audience Expansion",
                ],
            )
        )
        recommendations.append(
            AudienceRecommendation(
                segment_name=name,
                strategy="Use persona-specific proof points and a clear commercial wedge",
                channels=(
                    ["email", "paid_social"] if index % 2 == 0 else ["search", "email"]
                ),
                timing="Mid-week mornings",
                rationale=f"{name} scores well on value and engagement in the demo dataset",
            )
        )

    if input_data.analyze_overlap and len(segments) > 1:
        for left, right in zip(segments, segments[1:]):
            overlaps.append(
                SegmentOverlap(
                    segment_a_id=left.segment_id,
                    segment_b_id=right.segment_id,
                    overlap_count=max(10, min(left.size, right.size) // 6),
                    overlap_percentage=round(100 * 0.16, 2),
                )
            )
    return segments, overlaps, recommendations


def _requested_fetch_metrics(metrics: Iterable[MetricType]) -> List[str]:
    """Expand requested metrics into raw fields required by integrations."""
    requested = {metric.value for metric in metrics}
    fetch_metrics = set(requested)
    if "ctr" in requested:
        fetch_metrics.update({"impressions", "clicks"})
    if "conversion_rate" in requested:
        fetch_metrics.update({"clicks", "conversions"})
    if "roi" in requested:
        fetch_metrics.update({"cost", "revenue"})
    return sorted(
        fetch_metrics
        & {"impressions", "clicks", "conversions", "cost", "revenue", "reach"}
    )


async def generate_campaign_report(
    input_data: GenerateCampaignReportInput,
) -> GenerateCampaignReportOutput:
    """Generate comprehensive performance reports from campaign data."""
    mode = _mode_from_config()
    if mode == ExecutionMode.DEMO:
        campaigns = _demo_campaign_metrics(input_data)
        return GenerateCampaignReportOutput(
            status=ExecutionStatus.OK,
            mode=ExecutionMode.DEMO,
            report_id=_stable_id("report", *input_data.campaign_ids),
            generated_at=_utcnow(),
            date_range=input_data.date_range,
            campaigns=campaigns,
            summary=_build_report_summary(campaigns),
            charts=(
                _build_report_charts(campaigns) if input_data.include_charts else None
            ),
            format=input_data.format,
            download_url=None,
            warnings=["Demo mode uses deterministic sample campaign data."],
        )

    client, connected, warnings = await _connect_available_platforms()
    if not connected:
        return _blocked_report(
            input_data,
            "No configured marketing platform credentials were available for live reporting.",
            warnings,
        )

    try:
        metrics = _requested_fetch_metrics(input_data.metrics)
        results = await client.fetch_campaign_performance(
            campaign_ids=input_data.campaign_ids,
            start_date=datetime.fromisoformat(input_data.date_range["start"]),
            end_date=datetime.fromisoformat(input_data.date_range["end"]),
            metrics=metrics,
            platforms=connected,
        )
    finally:
        await client.disconnect_all()

    campaigns = _aggregate_campaign_rows(results.get("results", {}))
    warnings.extend(
        f"{platform}: {message}"
        for platform, message in results.get("errors", {}).items()
    )
    if not campaigns:
        return _blocked_report(
            input_data,
            "No live campaign performance data was returned from the configured platforms.",
            warnings,
        )

    _persist_campaign_snapshots(
        campaigns,
        input_data.date_range["start"],
        input_data.date_range["end"],
    )
    live_warnings = warnings[:]
    if input_data.format != ReportFormat.JSON:
        live_warnings.append(
            "Report export artifact generation is not implemented in the live tool path yet."
        )
    return GenerateCampaignReportOutput(
        status=ExecutionStatus.OK,
        mode=ExecutionMode.LIVE,
        report_id=str(uuid.uuid4()),
        generated_at=_utcnow(),
        date_range=input_data.date_range,
        campaigns=campaigns,
        summary=_build_report_summary(campaigns),
        charts=_build_report_charts(campaigns) if input_data.include_charts else None,
        format=input_data.format,
        download_url=None,
        warnings=live_warnings,
    )


def _allocation_scores(
    campaigns: Sequence[CampaignMetrics], goal: OptimizationGoal
) -> Dict[str, float]:
    """Create stable score weights for budget allocation."""
    scores: Dict[str, float] = {}
    for campaign in campaigns:
        if goal == OptimizationGoal.MAXIMIZE_CONVERSIONS:
            score = campaign.conversions + max(campaign.ctr, 0.1)
        elif goal == OptimizationGoal.MAXIMIZE_REACH:
            score = (campaign.reach or campaign.impressions or 1) + max(
                campaign.ctr, 0.1
            )
        else:
            score = (
                max(campaign.roi, 1.0) + campaign.conversions + max(campaign.ctr, 0.1)
            )
        scores[campaign.campaign_id] = max(score, 1.0)
    return scores


def _build_allocations(
    campaigns: Sequence[CampaignMetrics],
    total_budget: float,
    goal: OptimizationGoal,
    suggestions_by_campaign: Dict[str, Dict[str, object]],
    constraints: Dict[str, Dict[str, float]],
) -> List[BudgetAllocation]:
    """Build budget allocations from campaign scores and optional AI suggestions."""
    scores = _allocation_scores(campaigns, goal)
    total_score = sum(scores.values()) or 1.0
    allocations: List[BudgetAllocation] = []
    current_budget = total_budget / len(campaigns)
    for campaign in campaigns:
        recommended_budget = total_budget * (scores[campaign.campaign_id] / total_score)
        campaign_constraints = constraints.get(campaign.campaign_id, {})
        min_budget = campaign_constraints.get("min", 0.0)
        max_budget = campaign_constraints.get("max", total_budget)
        recommended_budget = max(min_budget, min(max_budget, recommended_budget))
        suggestion = suggestions_by_campaign.get(campaign.campaign_id, {})
        reasoning = suggestion.get(
            "reasoning",
            f"Allocated using {goal.value} score derived from live campaign performance.",
        )
        expected_impact = suggestion.get(
            "predicted_impact",
            {
                "roi_change": round(max(campaign.roi / 10, 2.0), 2),
                "conversion_change": round(max(campaign.conversions / 10, 1.0), 2),
                "cost_change": round(
                    ((recommended_budget - current_budget) / current_budget) * 100, 2
                ),
            },
        )
        allocations.append(
            BudgetAllocation(
                campaign_id=campaign.campaign_id,
                campaign_name=campaign.campaign_name,
                current_budget=round(current_budget, 2),
                recommended_budget=round(recommended_budget, 2),
                change_percentage=round(
                    ((recommended_budget - current_budget) / current_budget) * 100, 2
                ),
                expected_impact=expected_impact,
                reasoning=str(reasoning),
            )
        )
    return allocations


def _normalize_allocations(
    allocations: List[BudgetAllocation], total_budget: float
) -> List[BudgetAllocation]:
    """Normalize allocations so the total matches the requested budget."""
    recommended_total = sum(allocation.recommended_budget for allocation in allocations)
    if not allocations or recommended_total == 0:
        return allocations
    scale_factor = total_budget / recommended_total
    for allocation in allocations:
        allocation.recommended_budget = round(
            allocation.recommended_budget * scale_factor, 2
        )
        allocation.change_percentage = round(
            (
                (allocation.recommended_budget - allocation.current_budget)
                / allocation.current_budget
            )
            * 100,
            2,
        )
    return allocations


def _persist_optimization_decision(
    allocations: Sequence[BudgetAllocation],
    projected_improvement: ProjectedImprovement,
    total_budget: float,
    optimization_goal: OptimizationGoal,
):
    """Persist one optimization decision record into the database."""
    db = DatabaseManager()
    decision_id = _stable_id(
        "optimization-decision",
        optimization_goal.value,
        f"{total_budget:.2f}",
        *[
            f"{allocation.campaign_id}:{allocation.recommended_budget:.2f}"
            for allocation in sorted(allocations, key=lambda item: item.campaign_id)
        ],
    )
    db.record_ai_decision(
        decision_type=DecisionType.BUDGET_ALLOCATION,
        input_data={"allocations_requested": len(allocations)},
        decision_made={
            "allocations": [
                {
                    "campaign_id": allocation.campaign_id,
                    "recommended_budget": allocation.recommended_budget,
                    "reasoning": allocation.reasoning,
                }
                for allocation in allocations
            ]
        },
        confidence_score=0.8,
        reasoning="Budget allocations generated from live metrics and provider-backed optimization suggestions.",
        expected_impact=projected_improvement.model_dump(),
        campaign_id=None,
        decision_id=decision_id,
    )


async def optimize_campaign_budget(
    input_data: OptimizeCampaignBudgetInput,
) -> OptimizeCampaignBudgetOutput:
    """Use AI to suggest optimal budget reallocations."""
    mode = _mode_from_config()
    if mode == ExecutionMode.DEMO:
        campaigns = _demo_campaign_metrics(
            GenerateCampaignReportInput(
                campaign_ids=input_data.campaign_ids,
                date_range={
                    "start": (_utcnow() - timedelta(days=input_data.historical_days))
                    .date()
                    .isoformat(),
                    "end": _utcnow().date().isoformat(),
                },
                metrics=[
                    MetricType.IMPRESSIONS,
                    MetricType.CLICKS,
                    MetricType.CONVERSIONS,
                    MetricType.COST,
                    MetricType.REVENUE,
                ],
            )
        )
        allocations = _normalize_allocations(
            _build_allocations(
                campaigns=campaigns,
                total_budget=input_data.total_budget,
                goal=input_data.optimization_goal,
                suggestions_by_campaign={},
                constraints=input_data.constraints,
            ),
            input_data.total_budget,
        )
        return OptimizeCampaignBudgetOutput(
            status=ExecutionStatus.OK,
            mode=ExecutionMode.DEMO,
            optimization_id=_stable_id("optimization", *input_data.campaign_ids),
            total_budget=input_data.total_budget,
            optimization_goal=input_data.optimization_goal,
            allocations=allocations,
            projected_improvement=ProjectedImprovement(
                roi_change=12.0,
                conversion_change=9.0,
                reach_change=6.0,
                cpa_change=-8.0,
            ),
            confidence_score=0.78,
            recommendations=[
                "Demo mode ranked campaigns by deterministic performance scores.",
                "Use live mode with provider credentials for provider-backed optimization logic.",
            ],
            warnings=["Demo mode uses deterministic sample campaign data."],
        )

    client, connected, warnings = await _connect_available_platforms()
    if not connected:
        return _blocked_optimization(
            input_data,
            "Live optimization requires at least one configured marketing platform.",
            warnings,
        )

    try:
        results = await client.fetch_campaign_performance(
            campaign_ids=input_data.campaign_ids,
            start_date=_utcnow() - timedelta(days=input_data.historical_days),
            end_date=_utcnow(),
            metrics=[
                "impressions",
                "clicks",
                "conversions",
                "cost",
                "revenue",
                "reach",
            ],
            platforms=connected,
        )
    finally:
        await client.disconnect_all()

    campaigns = _aggregate_campaign_rows(results.get("results", {}))
    warnings.extend(
        f"{platform}: {message}"
        for platform, message in results.get("errors", {}).items()
    )
    if not campaigns:
        return _blocked_optimization(
            input_data,
            "Live optimization could not retrieve enough campaign performance data.",
            warnings,
        )

    try:
        ai_engine = MarketingAIEngine()
        analyzed = await ai_engine.analyze_campaign_performance(
            campaigns=[
                {
                    "campaign_id": campaign.campaign_id,
                    "campaign_name": campaign.campaign_name,
                    "metrics": campaign.model_dump(
                        include={
                            "impressions",
                            "clicks",
                            "conversions",
                            "cost",
                            "revenue",
                        }
                    ),
                }
                for campaign in campaigns
            ],
            start_date=_utcnow() - timedelta(days=input_data.historical_days),
            end_date=_utcnow(),
        )
        suggestions = await ai_engine.generate_optimization_suggestions(
            campaigns=analyzed,
            total_budget=input_data.total_budget,
            optimization_goal=input_data.optimization_goal.value,
        )
    except AIProviderNotConfiguredError as exc:
        return _blocked_optimization(input_data, str(exc), warnings)

    suggestions_by_campaign = {
        suggestion.campaign_id: {
            "reasoning": suggestion.reasoning,
            "predicted_impact": suggestion.predicted_impact,
            "action": suggestion.action,
        }
        for suggestion in suggestions
    }
    allocations = _normalize_allocations(
        _build_allocations(
            campaigns=campaigns,
            total_budget=input_data.total_budget,
            goal=input_data.optimization_goal,
            suggestions_by_campaign=suggestions_by_campaign,
            constraints=input_data.constraints,
        ),
        input_data.total_budget,
    )
    projected = ProjectedImprovement(
        roi_change=round(
            sum(
                allocation.expected_impact.get("roi_change", 0.0)
                for allocation in allocations
            )
            / max(len(allocations), 1),
            2,
        ),
        conversion_change=round(
            sum(
                allocation.expected_impact.get("conversion_change", 0.0)
                for allocation in allocations
            )
            / max(len(allocations), 1),
            2,
        ),
        reach_change=round(
            sum(max(allocation.change_percentage, 0.0) for allocation in allocations)
            / max(len(allocations), 1),
            2,
        ),
        cpa_change=round(
            -sum(
                allocation.expected_impact.get("cost_change", 0.0)
                for allocation in allocations
            )
            / max(len(allocations), 1),
            2,
        ),
    )
    _persist_optimization_decision(
        allocations,
        projected,
        input_data.total_budget,
        input_data.optimization_goal,
    )
    return OptimizeCampaignBudgetOutput(
        status=ExecutionStatus.OK,
        mode=ExecutionMode.LIVE,
        optimization_id=str(uuid.uuid4()),
        total_budget=input_data.total_budget,
        optimization_goal=input_data.optimization_goal,
        allocations=allocations,
        projected_improvement=projected,
        confidence_score=round(
            sum(
                suggestions_by_campaign.get(allocation.campaign_id, {})
                .get("predicted_impact", {})
                .get("roi_change", 0.0)
                >= 0
                for allocation in allocations
            )
            / max(len(allocations), 1),
            2,
        ),
        recommendations=[
            suggestion_by_campaign["action"]
            for suggestion_by_campaign in suggestions_by_campaign.values()
            if suggestion_by_campaign.get("action")
        ],
        warnings=warnings,
    )


async def create_campaign_copy(
    input_data: CreateCampaignCopyInput,
) -> CreateCampaignCopyOutput:
    """Generate marketing copy variants using the configured AI provider or demo mode."""
    mode = _mode_from_config()
    if mode == ExecutionMode.DEMO:
        variants = [
            _build_demo_copy_variant(input_data, index)
            for index in range(input_data.variants_count)
        ]
        best_variant = max(
            variants, key=lambda variant: variant.tone_match_score, default=None
        )
        return CreateCampaignCopyOutput(
            status=ExecutionStatus.OK,
            mode=ExecutionMode.DEMO,
            copy_generation_id=_stable_id(
                "copy-generation", input_data.product_name, input_data.copy_type
            ),
            copy_type=input_data.copy_type,
            variants=variants,
            tone=input_data.tone,
            target_audience=input_data.target_audience,
            keywords_used=input_data.keywords,
            best_variant_id=best_variant.variant_id if best_variant else None,
            generation_metadata={"provider": "demo", "model": "deterministic-demo"},
            warnings=["Demo mode uses deterministic sample copy templates."],
        )

    try:
        ai_engine = MarketingAIEngine()
        provider_variants = await ai_engine.create_personalized_ad_copy(
            product_name=input_data.product_name,
            product_description=input_data.product_description,
            target_audience={"description": input_data.target_audience},
            platform="google_ads",
            num_variants=input_data.variants_count,
            tone=input_data.tone.value,
        )
    except AIProviderNotConfiguredError as exc:
        return _blocked_copy(input_data, str(exc))

    variants = []
    for index, variant in enumerate(provider_variants):
        content = f"{variant.headline}: {variant.description}"
        if input_data.max_length and len(content) > input_data.max_length:
            content = f"{content[: input_data.max_length - 3]}..."
        variants.append(
            CopyVariant(
                variant_id=_stable_id(
                    "provider-copy", input_data.product_name, str(index)
                ),
                content=content,
                tone_match_score=round(0.88 + min(index, 3) * 0.02, 2),
                predicted_ctr=variant.predicted_ctr,
                keywords=variant.keywords,
                key_elements=[
                    variant.headline,
                    variant.call_to_action,
                    input_data.tone.value,
                ],
                character_count=len(content),
                word_count=len(content.split()),
                headline=variant.headline,
                call_to_action=variant.call_to_action,
            )
        )
    best_variant = max(
        variants, key=lambda item: item.predicted_ctr or 0.0, default=None
    )
    return CreateCampaignCopyOutput(
        status=ExecutionStatus.OK,
        mode=ExecutionMode.LIVE,
        copy_generation_id=str(uuid.uuid4()),
        copy_type=input_data.copy_type,
        variants=variants,
        tone=input_data.tone,
        target_audience=input_data.target_audience,
        keywords_used=input_data.keywords,
        best_variant_id=best_variant.variant_id if best_variant else None,
        generation_metadata={
            "provider": get_config().ai.provider,
            "model": ai_engine.model,
        },
    )


async def analyze_audience_segments(
    input_data: AnalyzeAudienceSegmentsInput,
) -> AnalyzeAudienceSegmentsOutput:
    """Analyze audience segments."""
    mode = _mode_from_config()
    if mode != ExecutionMode.DEMO:
        return _blocked_segments(
            input_data,
            "Live audience segmentation is not wired to a contact source in this repo. Use DEMO_MODE=true or add a contact integration.",
        )

    segments, overlaps, recommendations = _demo_segments(input_data)
    total_contacts = sum(segment.size for segment in segments) + 420
    return AnalyzeAudienceSegmentsOutput(
        status=ExecutionStatus.OK,
        mode=ExecutionMode.DEMO,
        analysis_id=_stable_id("segments", input_data.contact_list_id),
        total_contacts=total_contacts,
        segments=segments,
        uncategorized_count=420,
        overlaps=overlaps or None,
        recommendations=recommendations if input_data.include_recommendations else [],
        insights=[
            f"Demo mode identified {len(segments)} deterministic audience segments.",
            f"Highest value segment: {max(segments, key=lambda segment: segment.value_score).name}",
            f"Most engaged segment: {max(segments, key=lambda segment: segment.engagement_score).name}",
        ],
        created_at=_utcnow(),
        warnings=["Demo mode uses deterministic sample audience data."],
    )
