"""Canonical Pydantic models for MCP marketing automation tools."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ReportFormat(str, Enum):
    """Supported report formats."""

    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class MetricType(str, Enum):
    """Supported campaign metrics."""

    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    CONVERSIONS = "conversions"
    COST = "cost"
    REVENUE = "revenue"
    CTR = "ctr"
    CONVERSION_RATE = "conversion_rate"
    ROI = "roi"
    REACH = "reach"


class ToneOfVoice(str, Enum):
    """Marketing copy tone options."""

    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    INFORMATIVE = "informative"
    PERSUASIVE = "persuasive"


class SegmentCriteria(str, Enum):
    """Audience segmentation criteria."""

    DEMOGRAPHICS = "demographics"
    BEHAVIOR = "behavior"
    ENGAGEMENT = "engagement"
    PURCHASE_HISTORY = "purchase_history"
    INTERESTS = "interests"
    LOCATION = "location"


class ExecutionStatus(str, Enum):
    """Tool execution status."""

    OK = "ok"
    BLOCKED = "blocked"


class ExecutionMode(str, Enum):
    """Execution mode for tool responses."""

    LIVE = "live"
    DEMO = "demo"


class OptimizationGoal(str, Enum):
    """Supported optimization goals."""

    MAXIMIZE_CONVERSIONS = "maximize_conversions"
    MAXIMIZE_ROI = "maximize_roi"
    MAXIMIZE_REACH = "maximize_reach"


class ToolExecutionMetadata(BaseModel):
    """Metadata included in every tool output."""

    status: ExecutionStatus = Field(default=ExecutionStatus.OK)
    mode: ExecutionMode = Field(default=ExecutionMode.LIVE)
    blocked_reason: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class GenerateCampaignReportInput(BaseModel):
    """Input schema for generate_campaign_report."""

    campaign_ids: List[str] = Field(..., min_length=1)
    date_range: Dict[str, str]
    metrics: List[MetricType] = Field(..., min_length=1)
    format: ReportFormat = ReportFormat.JSON
    include_charts: bool = True
    group_by: Optional[str] = Field(
        default="campaign",
        description="Group results by: 'day', 'week', 'month', or 'campaign'",
    )

    @field_validator("date_range")
    @classmethod
    def validate_date_range(cls, value: Dict[str, str]) -> Dict[str, str]:
        if "start" not in value or "end" not in value:
            raise ValueError("date_range must have 'start' and 'end' keys")
        datetime.fromisoformat(value["start"])
        datetime.fromisoformat(value["end"])
        return value


class OptimizeCampaignBudgetInput(BaseModel):
    """Input schema for optimize_campaign_budget."""

    campaign_ids: List[str] = Field(..., min_length=1)
    total_budget: float = Field(..., gt=0)
    optimization_goal: OptimizationGoal = OptimizationGoal.MAXIMIZE_ROI
    constraints: Dict[str, Any] = Field(default_factory=dict)
    historical_days: int = Field(default=30, ge=7)
    include_projections: bool = True


class CreateCampaignCopyInput(BaseModel):
    """Input schema for create_campaign_copy."""

    product_name: str
    product_description: str
    target_audience: str
    tone: ToneOfVoice
    copy_type: str
    variants_count: int = Field(default=3, ge=1, le=10)
    keywords: List[str] = Field(default_factory=list)
    max_length: Optional[int] = None
    call_to_action: Optional[str] = None


class AnalyzeAudienceSegmentsInput(BaseModel):
    """Input schema for analyze_audience_segments."""

    contact_list_id: str
    criteria: List[SegmentCriteria] = Field(..., min_length=1)
    min_segment_size: int = Field(default=100, ge=10)
    max_segments: int = Field(default=10, ge=2, le=20)
    include_recommendations: bool = True
    analyze_overlap: bool = True


class CampaignMetrics(BaseModel):
    """Aggregated campaign performance metrics."""

    campaign_id: str
    campaign_name: str
    platform: Optional[str] = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    cost: float = 0.0
    revenue: float = 0.0
    ctr: float = 0.0
    conversion_rate: float = 0.0
    roi: float = 0.0
    reach: Optional[float] = None


class GenerateCampaignReportOutput(ToolExecutionMetadata):
    """Output schema for generate_campaign_report."""

    report_id: str
    generated_at: datetime
    date_range: Dict[str, str]
    campaigns: List[CampaignMetrics]
    summary: Dict[str, Any]
    charts: Optional[List[Dict[str, Any]]] = None
    format: ReportFormat
    download_url: Optional[str] = None


class BudgetAllocation(BaseModel):
    """Budget allocation recommendation for a campaign."""

    campaign_id: str
    campaign_name: str
    current_budget: float
    recommended_budget: float
    change_percentage: float
    expected_impact: Dict[str, float]
    reasoning: str


class ProjectedImprovement(BaseModel):
    """Projected account-level improvement from optimization."""

    roi_change: float = 0.0
    conversion_change: float = 0.0
    reach_change: float = 0.0
    cpa_change: float = 0.0


class OptimizeCampaignBudgetOutput(ToolExecutionMetadata):
    """Output schema for optimize_campaign_budget."""

    optimization_id: str
    total_budget: float
    optimization_goal: OptimizationGoal
    allocations: List[BudgetAllocation]
    projected_improvement: ProjectedImprovement
    confidence_score: float
    recommendations: List[str]


class CopyVariant(BaseModel):
    """A single copy variant."""

    variant_id: str
    content: str
    tone_match_score: float
    predicted_ctr: Optional[float] = None
    keywords: List[str] = Field(default_factory=list)
    key_elements: List[str] = Field(default_factory=list)
    character_count: int
    word_count: int
    headline: Optional[str] = None
    call_to_action: Optional[str] = None


class CreateCampaignCopyOutput(ToolExecutionMetadata):
    """Output schema for create_campaign_copy."""

    copy_generation_id: str
    copy_type: str
    variants: List[CopyVariant]
    tone: ToneOfVoice
    target_audience: str
    keywords_used: List[str]
    best_variant_id: Optional[str]
    generation_metadata: Dict[str, Any]


class AudienceSegment(BaseModel):
    """A single audience segment."""

    segment_id: str
    name: str
    size: int
    criteria: Dict[str, Any]
    characteristics: Dict[str, Any]
    engagement_score: float
    value_score: float
    recommended_campaigns: List[str]


class SegmentOverlap(BaseModel):
    """Overlap information between segments."""

    segment_a_id: str
    segment_b_id: str
    overlap_count: int
    overlap_percentage: float


class AudienceRecommendation(BaseModel):
    """Structured recommendation for an audience segment."""

    segment_name: str
    strategy: str
    channels: List[str]
    timing: str
    rationale: str


class AnalyzeAudienceSegmentsOutput(ToolExecutionMetadata):
    """Output schema for analyze_audience_segments."""

    analysis_id: str
    total_contacts: int
    segments: List[AudienceSegment]
    uncategorized_count: int
    overlaps: Optional[List[SegmentOverlap]] = None
    recommendations: List[AudienceRecommendation]
    insights: List[str]
    created_at: datetime
