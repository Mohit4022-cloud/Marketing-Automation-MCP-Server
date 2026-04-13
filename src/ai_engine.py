"""AI engine for provider-backed marketing decision support."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from typing import Any, Dict, List, Optional

from jinja2 import Template
from pydantic import BaseModel

from .ai.providers import BaseAIProvider, ProviderRegistry

logger = logging.getLogger(__name__)


class DecisionType(str, Enum):
    """Types of marketing decisions the AI can make."""

    CAMPAIGN_ANALYSIS = "campaign_analysis"
    BUDGET_OPTIMIZATION = "budget_optimization"
    AD_COPY_GENERATION = "ad_copy_generation"
    AUDIENCE_TARGETING = "audience_targeting"
    TREND_PREDICTION = "trend_prediction"


class PromptTemplate(BaseModel):
    """Prompt template structure."""

    name: str
    template: str
    variables: List[str]
    description: str
    category: DecisionType


@dataclass
class CampaignPerformance:
    """Campaign performance metrics structure."""

    campaign_id: str
    campaign_name: str
    impressions: int
    clicks: int
    conversions: int
    cost: float
    revenue: float
    ctr: float
    conversion_rate: float
    roi: float
    trend: str


@dataclass
class OptimizationSuggestion:
    """Optimization suggestion structure."""

    type: str
    campaign_id: str
    action: str
    predicted_impact: Dict[str, float]
    confidence: float
    reasoning: str
    implementation_steps: List[str]


@dataclass
class AdCopyVariant:
    """Ad copy variant structure."""

    headline: str
    description: str
    call_to_action: str
    target_audience: str
    tone: str
    predicted_ctr: float
    keywords: List[str]


class MarketingAIEngine:
    """
    Provider-backed AI engine for structured marketing analysis.

    The engine keeps marketing prompts and orchestration in one place while
    delegating actual model execution to provider adapters.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        provider_name: Optional[str] = None,
        provider: Optional[BaseAIProvider] = None,
    ):
        self.provider = provider or ProviderRegistry().get_provider(
            provider_name=provider_name, model_override=model
        )
        self.model = self.provider.model
        self.prompt_templates = self._initialize_prompt_templates()

    def _initialize_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """Initialize prompt templates for different marketing tasks."""
        return {
            "campaign_analysis": PromptTemplate(
                name="campaign_analysis",
                template="""Analyze the following campaign performance data and identify trends.

Campaign Data:
{{ campaign_data | tojson(indent=2) }}

Time Period: {{ start_date }} to {{ end_date }}
Benchmarks: {{ benchmarks | tojson(indent=2) }}

Focus on actionable insights that explain which campaigns are improving, which are declining, and why.""",
                variables=["campaign_data", "start_date", "end_date", "benchmarks"],
                description="Analyze campaign performance and identify trends",
                category=DecisionType.CAMPAIGN_ANALYSIS,
            ),
            "budget_optimization": PromptTemplate(
                name="budget_optimization",
                template="""Recommend budget allocation across these campaigns.

Campaigns:
{{ campaigns | tojson(indent=2) }}

Total Budget: {{ total_budget }}
Optimization Goal: {{ optimization_goal }}
Constraints: {{ constraints | tojson(indent=2) }}
Historical Context: {{ historical_data | tojson(indent=2) }}

Prioritize explainable recommendations and realistic budget changes.""",
                variables=[
                    "campaigns",
                    "total_budget",
                    "optimization_goal",
                    "constraints",
                    "historical_data",
                ],
                description="Generate optimization suggestions with predicted impact",
                category=DecisionType.BUDGET_OPTIMIZATION,
            ),
            "ad_copy_generation": PromptTemplate(
                name="ad_copy_generation",
                template="""Create ad copy variants for the following offer.

Product: {{ product_name }}
Description: {{ product_description }}
Target Audience: {{ target_audience }}
Key Benefits: {{ key_benefits | join(", ") }}
Tone: {{ tone }}
Platform: {{ platform }}
Headline Limit: {{ headline_limit }}
Description Limit: {{ description_limit }}
Audience Insights: {{ audience_insights | tojson(indent=2) }}

Generate variants that are commercially specific, concise, and high signal.""",
                variables=[
                    "product_name",
                    "product_description",
                    "target_audience",
                    "key_benefits",
                    "tone",
                    "platform",
                    "headline_limit",
                    "description_limit",
                    "audience_insights",
                ],
                description="Generate personalized ad copy variants",
                category=DecisionType.AD_COPY_GENERATION,
            ),
            "trend_prediction": PromptTemplate(
                name="trend_prediction",
                template="""Summarize the likely forward trend from this historical marketing data.

Historical Data:
{{ historical_data | tojson(indent=2) }}

Seasonality: {{ seasonality_data | tojson(indent=2) }}
Market Trends: {{ market_trends | tojson(indent=2) }}
Competitive Data: {{ competitive_data | tojson(indent=2) }}
Prediction Period: {{ prediction_period }}
""",
                variables=[
                    "historical_data",
                    "seasonality_data",
                    "market_trends",
                    "competitive_data",
                    "prediction_period",
                ],
                description="Predict future campaign performance trends",
                category=DecisionType.TREND_PREDICTION,
            ),
        }

    def get_prompt_template(self, template_name: str) -> PromptTemplate:
        """Get a specific prompt template."""
        if template_name not in self.prompt_templates:
            raise ValueError(f"Template '{template_name}' not found")
        return self.prompt_templates[template_name]

    def render_prompt(self, template_name: str, **kwargs) -> str:
        """Render a prompt template with provided variables."""
        prompt_template = self.get_prompt_template(template_name)
        missing_vars = set(prompt_template.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        return Template(prompt_template.template).render(**kwargs)

    async def analyze_campaign_performance(
        self,
        campaigns: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        benchmarks: Optional[Dict[str, float]] = None,
    ) -> List[CampaignPerformance]:
        """Analyze campaign performance and classify each campaign trend."""
        prompt = self.render_prompt(
            "campaign_analysis",
            campaign_data=[
                {
                    "campaign_id": campaign["campaign_id"],
                    "campaign_name": campaign["campaign_name"],
                    **campaign.get("metrics", {}),
                }
                for campaign in campaigns
            ],
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            benchmarks=benchmarks
            or {"ctr": 2.0, "conversion_rate": 3.0, "roi": 200.0},
        )
        schema = {
            "type": "object",
            "properties": {
                "campaigns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "campaign_id": {"type": "string"},
                            "campaign_name": {"type": "string"},
                            "impressions": {"type": "integer"},
                            "clicks": {"type": "integer"},
                            "conversions": {"type": "integer"},
                            "cost": {"type": "number"},
                            "revenue": {"type": "number"},
                            "ctr": {"type": "number"},
                            "conversion_rate": {"type": "number"},
                            "roi": {"type": "number"},
                            "trend": {
                                "type": "string",
                                "enum": ["improving", "declining", "stable"],
                            },
                        },
                        "required": [
                            "campaign_id",
                            "campaign_name",
                            "impressions",
                            "clicks",
                            "conversions",
                            "cost",
                            "revenue",
                            "ctr",
                            "conversion_rate",
                            "roi",
                            "trend",
                        ],
                    },
                }
            },
            "required": ["campaigns"],
        }
        payload = await self.provider.generate_structured(
            system_prompt=(
                "You are a marketing analytics expert. Return only structured data."
            ),
            user_prompt=prompt,
            schema=schema,
        )
        return [CampaignPerformance(**campaign) for campaign in payload["campaigns"]]

    async def generate_optimization_suggestions(
        self,
        campaigns: List[CampaignPerformance],
        total_budget: float,
        optimization_goal: str = "maximize_roi",
    ) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions with predicted impact."""
        prompt = self.render_prompt(
            "budget_optimization",
            campaigns=[
                asdict(campaign)
                if hasattr(campaign, "__dataclass_fields__")
                else campaign
                for campaign in campaigns
            ],
            total_budget=total_budget,
            optimization_goal=optimization_goal,
            constraints={"min_budget": 100, "max_budget_per_campaign": total_budget * 0.5},
            historical_data=[],
        )
        schema = {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "campaign_id": {"type": "string"},
                            "action": {"type": "string"},
                            "predicted_impact": {
                                "type": "object",
                                "properties": {
                                    "roi_change": {"type": "number"},
                                    "conversion_change": {"type": "number"},
                                    "cost_change": {"type": "number"},
                                },
                                "required": [
                                    "roi_change",
                                    "conversion_change",
                                    "cost_change",
                                ],
                            },
                            "confidence": {"type": "number"},
                            "reasoning": {"type": "string"},
                            "implementation_steps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "type",
                            "campaign_id",
                            "action",
                            "predicted_impact",
                            "confidence",
                            "reasoning",
                            "implementation_steps",
                        ],
                    },
                }
            },
            "required": ["suggestions"],
        }
        payload = await self.provider.generate_structured(
            system_prompt=(
                "You are a marketing optimization expert. Return structured reallocation guidance."
            ),
            user_prompt=prompt,
            schema=schema,
        )
        return [OptimizationSuggestion(**suggestion) for suggestion in payload["suggestions"]]

    async def create_personalized_ad_copy(
        self,
        product_name: str,
        product_description: str,
        target_audience: Dict[str, Any],
        platform: str = "google_ads",
        num_variants: int = 3,
        tone: str = "professional",
    ) -> List[AdCopyVariant]:
        """Create personalized ad copy based on audience segments."""
        platform_limits = {
            "google_ads": {"headline": 30, "description": 90},
            "facebook_ads": {"headline": 40, "description": 125},
            "linkedin_ads": {"headline": 50, "description": 100},
        }
        limits = platform_limits.get(platform, platform_limits["google_ads"])
        prompt = self.render_prompt(
            "ad_copy_generation",
            product_name=product_name,
            product_description=product_description,
            target_audience=target_audience,
            key_benefits=["Improve efficiency", "Increase ROI", "Reduce manual work"],
            tone=tone,
            platform=platform,
            headline_limit=limits["headline"],
            description_limit=limits["description"],
            audience_insights=target_audience,
        )
        schema = {
            "type": "object",
            "properties": {
                "variants": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "description": {"type": "string"},
                            "call_to_action": {"type": "string"},
                            "target_audience": {"type": "string"},
                            "tone": {"type": "string"},
                            "predicted_ctr": {"type": "number"},
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "headline",
                            "description",
                            "call_to_action",
                            "target_audience",
                            "tone",
                            "predicted_ctr",
                            "keywords",
                        ],
                    },
                    "minItems": num_variants,
                }
            },
            "required": ["variants"],
        }
        payload = await self.provider.generate_structured(
            system_prompt=(
                "You write concise, commercially specific ad copy and return structured output only."
            ),
            user_prompt=prompt,
            schema=schema,
        )
        return [AdCopyVariant(**variant) for variant in payload["variants"][:num_variants]]

    async def execute_prompt_chain(
        self,
        chain_name: str,
        initial_data: Dict[str, Any],
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a chain of prompts for complex decision-making."""
        results = {"chain_name": chain_name, "steps": []}
        context = initial_data.copy()

        for index, step in enumerate(steps):
            step_name = step.get("name", f"step_{index}")
            template_name = step["template"]
            variables = step.get("variables", {}).copy()
            for key, value in list(variables.items()):
                if isinstance(value, str) and value.startswith("$"):
                    path = value[1:].split(".")
                    if path[0] == "context":
                        variables[key] = self._get_nested_value(context, path[1:])
                    elif path[0] == "results":
                        variables[key] = self._get_nested_value(results, path[1:])

            step_vars = {**context, **variables}

            if template_name == "campaign_analysis":
                result = await self.analyze_campaign_performance(
                    campaigns=step_vars.get("campaigns", []),
                    start_date=step_vars.get("start_date"),
                    end_date=step_vars.get("end_date"),
                    benchmarks=step_vars.get("benchmarks"),
                )
            elif template_name == "budget_optimization":
                result = await self.generate_optimization_suggestions(
                    campaigns=step_vars.get("campaigns", []),
                    total_budget=step_vars.get("total_budget"),
                    optimization_goal=step_vars.get("optimization_goal", "maximize_roi"),
                )
            else:
                prompt = self.render_prompt(template_name, **step_vars)
                result = await self._execute_generic_prompt(
                    prompt, step.get("output_format")
                )

            serialized = (
                [asdict(item) for item in result]
                if isinstance(result, list)
                else result
            )
            step_result = {
                "step_name": step_name,
                "template": template_name,
                "result": serialized,
            }
            results["steps"].append(step_result)
            if step.get("update_context"):
                context[step_name] = serialized

        results["final_context"] = context
        return results

    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        """Get a nested value from a dictionary-like structure."""
        value: Any = data
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if idx < len(value) else None
            else:
                return None
        return value

    async def _execute_generic_prompt(
        self, prompt: str, output_format: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a generic prompt with optional structured output."""
        system_prompt = "You are a marketing automation AI assistant."
        if output_format:
            return await self.provider.generate_structured(
                system_prompt=system_prompt,
                user_prompt=prompt,
                schema=output_format,
            )
        return await self.provider.generate_text(
            system_prompt=system_prompt,
            user_prompt=prompt,
        )

    async def create_budget_reallocation_chain(
        self,
        campaigns: List[Dict[str, Any]],
        total_budget: float,
        business_goals: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a prompt chain for complex budget reallocation decisions."""
        chain_steps = [
            {
                "name": "performance_analysis",
                "template": "campaign_analysis",
                "variables": {
                    "campaigns": campaigns,
                    "start_date": datetime.now() - timedelta(days=30),
                    "end_date": datetime.now(),
                    "benchmarks": business_goals.get("benchmarks", {}),
                },
                "update_context": True,
            },
            {
                "name": "trend_prediction",
                "template": "trend_prediction",
                "variables": {
                    "historical_data": "$context.performance_analysis",
                    "seasonality_data": business_goals.get("seasonality", {}),
                    "market_trends": business_goals.get("market_trends", {}),
                    "competitive_data": {},
                    "prediction_period": "next_30_days",
                },
                "update_context": True,
                "output_format": {
                    "type": "object",
                    "properties": {
                        "trend_summary": {"type": "string"},
                        "risk_factors": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["trend_summary", "risk_factors"],
                },
            },
            {
                "name": "optimization",
                "template": "budget_optimization",
                "variables": {
                    "campaigns": "$context.performance_analysis",
                    "total_budget": total_budget,
                    "optimization_goal": business_goals.get(
                        "primary_goal", "maximize_roi"
                    ),
                    "constraints": business_goals.get("constraints", {}),
                    "historical_data": "$context.trend_prediction",
                },
                "update_context": True,
            },
        ]
        return await self.execute_prompt_chain(
            chain_name="budget_reallocation",
            initial_data={
                "total_budget": total_budget,
                "business_goals": business_goals,
            },
            steps=chain_steps,
        )


async def create_ai_engine() -> MarketingAIEngine:
    """Factory function for the AI engine."""
    return MarketingAIEngine()
