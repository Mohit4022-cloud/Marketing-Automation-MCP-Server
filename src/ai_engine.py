"""AI Engine for intelligent marketing decision-making using OpenAI's API"""

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
import openai
from jinja2 import Template
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DecisionType(str, Enum):
    """Types of marketing decisions the AI can make"""

    CAMPAIGN_ANALYSIS = "campaign_analysis"
    BUDGET_OPTIMIZATION = "budget_optimization"
    AD_COPY_GENERATION = "ad_copy_generation"
    AUDIENCE_TARGETING = "audience_targeting"
    TREND_PREDICTION = "trend_prediction"


class PromptTemplate(BaseModel):
    """Prompt template structure"""

    name: str
    template: str
    variables: List[str]
    description: str
    category: DecisionType


@dataclass
class CampaignPerformance:
    """Campaign performance metrics structure"""

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
    trend: str  # "improving", "declining", "stable"


@dataclass
class OptimizationSuggestion:
    """Optimization suggestion structure"""

    type: str
    campaign_id: str
    action: str
    predicted_impact: Dict[str, float]
    confidence: float
    reasoning: str
    implementation_steps: List[str]


@dataclass
class AdCopyVariant:
    """Ad copy variant structure"""

    headline: str
    description: str
    call_to_action: str
    target_audience: str
    tone: str
    predicted_ctr: float
    keywords: List[str]


class MarketingAIEngine:
    """
    AI Engine for intelligent marketing automation decisions.
    Uses OpenAI's function calling capabilities for structured outputs.
    """

    def __init__(self, model: str = "gpt-4-turbo-preview"):
        # Provider selection: OPENAI (default) or DIFY (self-hosted) or LOCAL
        self.llm_provider = os.getenv("LLM_PROVIDER", "OPENAI").upper()
        self.model = model
        self.prompt_templates = self._initialize_prompt_templates()

        # Configure provider-specific clients or endpoints
        if self.llm_provider == "OPENAI":
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable not set when LLM_PROVIDER=OPENAI"
                )
            # AsyncOpenAI client used for OpenAI provider
            self.client = AsyncOpenAI(api_key=self.api_key)
            # Dify attributes kept empty
            self.dify_api_url = ""
            self.dify_api_key = ""
            self.dify_model = ""
        elif self.llm_provider == "DIFY":
            # Dify (self-hosted) requires a URL and API key
            self.dify_api_url = os.getenv("DIFY_API_URL", "")
            self.dify_api_key = os.getenv("DIFY_API_KEY", "")
            self.dify_model = os.getenv("DIFY_MODEL", "")
            if not (self.dify_api_url and self.dify_api_key):
                raise ValueError(
                    "DIFY_API_URL and DIFY_API_KEY must be set when LLM_PROVIDER=DIFY"
                )
            self.client = None
        else:
            # LOCAL or other providers - no remote client by default
            self.client = None
            self.dify_api_url = os.getenv("DIFY_API_URL", "")
            self.dify_api_key = os.getenv("DIFY_API_KEY", "")
            self.dify_model = os.getenv("DIFY_MODEL", "")

    async def _call_llm(
        self, messages: List[Dict[str, str]], functions=None, function_call=None
    ):
        """
        Unified LLM call that routes to the selected provider.
        For OpenAI: returns the AsyncOpenAI response object.
        For Dify: returns a dict parsed from the HTTP JSON response (matching OpenAI-like structure).
        """
        if self.llm_provider == "OPENAI":
            # Use OpenAI Async client
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=functions,
                function_call=function_call,
            )
        elif self.llm_provider == "DIFY":
            # Construct payload similar to OpenAI's chat completions
            payload = {
                "model": self.dify_model if self.dify_model else self.model,
                "messages": messages,
            }
            if functions is not None:
                payload["functions"] = functions
            if function_call is not None:
                payload["function_call"] = function_call

            headers = {
                "Authorization": f"Bearer {self.dify_api_key}",
                "Content-Type": "application/json",
            }
            # Dify chat-completion endpoint commonly lives under /v1/chat/completions, but allow full URL
            post_url = self.dify_api_url.rstrip("/") + "/v1/chat/completions"
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(post_url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        else:
            raise RuntimeError(f"Unsupported LLM provider: {self.llm_provider}")

    def _initialize_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """Initialize prompt templates for different marketing tasks"""
        templates = {
            "campaign_analysis": PromptTemplate(
                name="campaign_analysis",
                template="""Analyze the following campaign performance data and identify trends:

Campaign Data:
{{ campaign_data | tojson(indent=2) }}

Time Period: {{ start_date }} to {{ end_date }}

Please analyze:
1. Performance trends (improving, declining, stable)
2. Key performance indicators that need attention
3. Anomalies or significant changes
4. Comparison with benchmarks: {{ benchmarks | tojson }}

Focus on actionable insights that can improve campaign performance.""",
                variables=["campaign_data", "start_date", "end_date", "benchmarks"],
                description="Analyzes campaign performance and identifies trends",
                category=DecisionType.CAMPAIGN_ANALYSIS,
            ),
            "budget_optimization": PromptTemplate(
                name="budget_optimization",
                template="""Optimize budget allocation across the following campaigns:

Current Campaign Performance:
{{ campaigns | tojson(indent=2) }}

Total Budget: ${{ total_budget }}
Optimization Goal: {{ optimization_goal }}
Constraints: {{ constraints | tojson }}

Historical Performance Trends:
{{ historical_data | tojson(indent=2) }}

Please provide:
1. Recommended budget allocation for each campaign
2. Expected impact on key metrics
3. Risk assessment
4. Implementation timeline
5. Alternative scenarios if applicable""",
                variables=[
                    "campaigns",
                    "total_budget",
                    "optimization_goal",
                    "constraints",
                    "historical_data",
                ],
                description="Optimizes budget allocation across campaigns",
                category=DecisionType.BUDGET_OPTIMIZATION,
            ),
            "ad_copy_generation": PromptTemplate(
                name="ad_copy_generation",
                template="""Generate compelling ad copy variants for the following product/service:

Product: {{ product_name }}
Description: {{ product_description }}
Target Audience: {{ target_audience }}
Key Benefits: {{ key_benefits | join(", ") }}
Tone: {{ tone }}
Platform: {{ platform }}
Character Limits: Headline - {{ headline_limit }}, Description - {{ description_limit }}

Audience Insights:
{{ audience_insights | tojson(indent=2) }}

Competitor Examples:
{{ competitor_ads | tojson(indent=2) }}

Generate {{ num_variants }} unique variants that:
1. Resonate with the target audience
2. Highlight key benefits
3. Include strong calls-to-action
4. Optimize for the platform's best practices""",
                variables=[
                    "product_name",
                    "product_description",
                    "target_audience",
                    "key_benefits",
                    "tone",
                    "platform",
                    "headline_limit",
                    "description_limit",
                    "num_variants",
                    "audience_insights",
                    "competitor_ads",
                ],
                description="Generates personalized ad copy based on audience segments",
                category=DecisionType.AD_COPY_GENERATION,
            ),
            "audience_targeting": PromptTemplate(
                name="audience_targeting",
                template="""Analyze and recommend audience targeting strategies:

Current Audience Data:
{{ audience_data | tojson(indent=2) }}

Campaign Objective: {{ objective }}
Product/Service: {{ product_info }}
Budget Range: {{ budget_range }}

Performance by Segment:
{{ segment_performance | tojson(indent=2) }}

Please recommend:
1. High-value audience segments to target
2. Segments to exclude or deprioritize
3. New audience opportunities based on data
4. Optimal targeting parameters for each platform
5. Estimated reach and impact""",
                variables=[
                    "audience_data",
                    "objective",
                    "product_info",
                    "budget_range",
                    "segment_performance",
                ],
                description="Recommends audience targeting strategies",
                category=DecisionType.AUDIENCE_TARGETING,
            ),
            "trend_prediction": PromptTemplate(
                name="trend_prediction",
                template="""Predict future campaign performance trends:

Historical Performance Data:
{{ historical_data | tojson(indent=2) }}

External Factors:
- Seasonality: {{ seasonality_data | tojson }}
- Market Trends: {{ market_trends | tojson }}
- Competitive Landscape: {{ competitive_data | tojson }}

Time Horizon: {{ prediction_period }}

Please provide:
1. Performance predictions for each metric
2. Confidence intervals
3. Key factors influencing predictions
4. Recommended proactive actions
5. Risk factors to monitor""",
                variables=[
                    "historical_data",
                    "seasonality_data",
                    "market_trends",
                    "competitive_data",
                    "prediction_period",
                ],
                description="Predicts future campaign performance trends",
                category=DecisionType.TREND_PREDICTION,
            ),
        }

        return templates

    def get_prompt_template(self, template_name: str) -> PromptTemplate:
        """Get a specific prompt template"""
        if template_name not in self.prompt_templates:
            raise ValueError(f"Template '{template_name}' not found")
        return self.prompt_templates[template_name]

    def render_prompt(self, template_name: str, **kwargs) -> str:
        """Render a prompt template with provided variables"""
        prompt_template = self.get_prompt_template(template_name)

        # Check all required variables are provided
        missing_vars = set(prompt_template.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        # Render template
        template = Template(prompt_template.template)
        return template.render(**kwargs)

    async def analyze_campaign_performance(
        self,
        campaigns: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        benchmarks: Optional[Dict[str, float]] = None,
    ) -> List[CampaignPerformance]:
        """Analyze campaign performance and identify underperforming campaigns"""

        # Default benchmarks if not provided
        if not benchmarks:
            benchmarks = {
                "ctr": 2.0,  # 2% CTR
                "conversion_rate": 3.0,  # 3% conversion rate
                "roi": 200.0,  # 200% ROI
            }

        # Prepare campaign data
        campaign_data = []
        for campaign in campaigns:
            metrics = campaign.get("metrics", {})
            campaign_data.append(
                {
                    "id": campaign["campaign_id"],
                    "name": campaign["campaign_name"],
                    "impressions": metrics.get("impressions", 0),
                    "clicks": metrics.get("clicks", 0),
                    "conversions": metrics.get("conversions", 0),
                    "cost": metrics.get("cost", 0),
                    "revenue": metrics.get("revenue", 0),
                }
            )

        # Render prompt
        prompt = self.render_prompt(
            "campaign_analysis",
            campaign_data=campaign_data,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            benchmarks=benchmarks,
        )

        # Define function for structured output
        functions = [
            {
                "name": "analyze_campaigns",
                "description": "Analyze campaign performance and return structured results",
                "parameters": {
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
                                    "issues": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "opportunities": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": ["campaign_id", "campaign_name", "trend"],
                            },
                        },
                        "summary": {
                            "type": "object",
                            "properties": {
                                "total_campaigns": {"type": "integer"},
                                "underperforming_count": {"type": "integer"},
                                "top_performers": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "key_insights": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["campaigns", "summary"],
                },
            }
        ]

        try:
            response = await self._call_llm(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a marketing analytics expert.",
                    },
                    {"role": "user", "content": prompt},
                ],
                functions=functions,
                function_call={"name": "analyze_campaigns"},
            )

            # Normalize and parse function call response across providers
            if self.llm_provider == "OPENAI":
                # OpenAI response object (python-openai) -> extract same way as before
                function_args_raw = response.choices[0].message.function_call.arguments
                function_args = json.loads(function_args_raw)
            else:
                # Dify (or other HTTP provider) returned a dict-like JSON
                # Expected path: response["choices"][0]["message"]["function_call"]["arguments"]
                fn = (
                    response.get("choices", [])[0]
                    .get("message", {})
                    .get("function_call", {})
                    .get("arguments")
                )
                if isinstance(fn, str):
                    function_args = json.loads(fn)
                else:
                    function_args = fn

            # Convert to CampaignPerformance objects
            performances = []
            for campaign in function_args["campaigns"]:
                performances.append(
                    CampaignPerformance(
                        **{
                            k: v
                            for k, v in campaign.items()
                            if k in CampaignPerformance.__dataclass_fields__
                        }
                    )
                )

            return performances

        except Exception as e:
            logger.error(f"Error analyzing campaign performance: {e}")
            raise

    async def generate_optimization_suggestions(
        self,
        campaigns: List[CampaignPerformance],
        total_budget: float,
        optimization_goal: str = "maximize_roi",
    ) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions with predicted impact"""

        # Prepare campaign data for prompt
        campaign_data = [asdict(campaign) for campaign in campaigns]

        prompt = self.render_prompt(
            "budget_optimization",
            campaigns=campaign_data,
            total_budget=total_budget,
            optimization_goal=optimization_goal,
            constraints={
                "min_budget": 100,
                "max_budget_per_campaign": total_budget * 0.5,
            },
            historical_data=[],  # Could be populated with actual historical data
        )

        functions = [
            {
                "name": "generate_suggestions",
                "description": "Generate optimization suggestions with predicted impact",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "suggestions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": [
                                            "budget_reallocation",
                                            "bid_adjustment",
                                            "targeting_change",
                                            "creative_refresh",
                                            "pause_campaign",
                                        ],
                                    },
                                    "campaign_id": {"type": "string"},
                                    "action": {"type": "string"},
                                    "predicted_impact": {
                                        "type": "object",
                                        "properties": {
                                            "roi_change": {"type": "number"},
                                            "conversion_change": {"type": "number"},
                                            "cost_change": {"type": "number"},
                                        },
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
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
                                ],
                            },
                        },
                        "budget_allocation": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                        "expected_overall_impact": {
                            "type": "object",
                            "properties": {
                                "total_roi": {"type": "number"},
                                "total_conversions": {"type": "number"},
                                "total_revenue": {"type": "number"},
                            },
                        },
                    },
                    "required": ["suggestions"],
                },
            }
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a marketing optimization expert specializing in budget allocation and campaign performance.",
                    },
                    {"role": "user", "content": prompt},
                ],
                functions=functions,
                function_call={"name": "generate_suggestions"},
            )

            function_args = json.loads(
                response.choices[0].message.function_call.arguments
            )

            # Convert to OptimizationSuggestion objects
            suggestions = []
            for suggestion in function_args["suggestions"]:
                suggestions.append(OptimizationSuggestion(**suggestion))

            return suggestions

        except Exception as e:
            logger.error(f"Error generating optimization suggestions: {e}")
            raise

    async def create_personalized_ad_copy(
        self,
        product_name: str,
        product_description: str,
        target_audience: Dict[str, Any],
        platform: str = "google_ads",
        num_variants: int = 3,
        tone: str = "professional",
    ) -> List[AdCopyVariant]:
        """Create personalized ad copy based on audience segments"""

        # Platform-specific character limits
        platform_limits = {
            "google_ads": {"headline": 30, "description": 90},
            "facebook_ads": {"headline": 40, "description": 125},
            "linkedin_ads": {"headline": 50, "description": 100},
        }

        limits = platform_limits.get(platform, platform_limits["google_ads"])

        # Extract key benefits from description
        key_benefits = [
            "High quality",
            "Cost-effective",
            "Easy to use",
        ]  # Could use NLP to extract

        prompt = self.render_prompt(
            "ad_copy_generation",
            product_name=product_name,
            product_description=product_description,
            target_audience=target_audience,
            key_benefits=key_benefits,
            tone=tone,
            platform=platform,
            headline_limit=limits["headline"],
            description_limit=limits["description"],
            num_variants=num_variants,
            audience_insights=target_audience,
            competitor_ads=[],  # Could be populated with competitor data
        )

        functions = [
            {
                "name": "generate_ad_copy",
                "description": "Generate personalized ad copy variants",
                "parameters": {
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
                                    "predicted_ctr": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 100,
                                    },
                                    "keywords": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "unique_selling_points": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": [
                                    "headline",
                                    "description",
                                    "call_to_action",
                                    "predicted_ctr",
                                ],
                            },
                        },
                        "recommendations": {
                            "type": "object",
                            "properties": {
                                "best_variant_index": {"type": "integer"},
                                "a_b_test_suggestion": {"type": "string"},
                                "platform_specific_tips": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["variants"],
                },
            }
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert copywriter specializing in digital advertising.",
                    },
                    {"role": "user", "content": prompt},
                ],
                functions=functions,
                function_call={"name": "generate_ad_copy"},
            )

            function_args = json.loads(
                response.choices[0].message.function_call.arguments
            )

            # Convert to AdCopyVariant objects
            variants = []
            for variant in function_args["variants"]:
                variants.append(
                    AdCopyVariant(
                        headline=variant["headline"],
                        description=variant["description"],
                        call_to_action=variant["call_to_action"],
                        target_audience=variant.get(
                            "target_audience", str(target_audience)
                        ),
                        tone=variant.get("tone", tone),
                        predicted_ctr=variant["predicted_ctr"],
                        keywords=variant.get("keywords", []),
                    )
                )

            return variants

        except Exception as e:
            logger.error(f"Error creating personalized ad copy: {e}")
            raise

    async def execute_prompt_chain(
        self, chain_name: str, initial_data: Dict[str, Any], steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a chain of prompts for complex decision-making"""

        results = {"chain_name": chain_name, "steps": []}
        context = initial_data.copy()

        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            template_name = step["template"]

            # Prepare variables for this step, including results from previous steps
            variables = step.get("variables", {})
            for key, value in variables.items():
                # Support referencing previous step results
                if isinstance(value, str) and value.startswith("$"):
                    path = value[1:].split(".")
                    if path[0] == "context":
                        variables[key] = self._get_nested_value(context, path[1:])
                    elif path[0] == "results":
                        variables[key] = self._get_nested_value(results, path[1:])

            # Merge with context
            step_vars = {**context, **variables}

            # Execute step based on template type
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
                    optimization_goal=step_vars.get(
                        "optimization_goal", "maximize_roi"
                    ),
                )
            else:
                # Generic prompt execution
                prompt = self.render_prompt(template_name, **step_vars)
                result = await self._execute_generic_prompt(
                    prompt, step.get("output_format")
                )

            # Store step result
            step_result = {
                "step_name": step_name,
                "template": template_name,
                "result": result
                if not isinstance(result, list)
                else [
                    asdict(r) if hasattr(r, "__dataclass_fields__") else r
                    for r in result
                ],
            }
            results["steps"].append(step_result)

            # Update context with step results if specified
            if step.get("update_context"):
                context[step_name] = step_result["result"]

        results["final_context"] = context
        return results

    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        """Get nested value from dictionary using path"""
        value = data
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                index = int(key)
                value = value[index] if index < len(value) else None
            else:
                return None
        return value

    async def _execute_generic_prompt(
        self, prompt: str, output_format: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a generic prompt with optional structured output"""
        messages = [
            {
                "role": "system",
                "content": "You are a marketing automation AI assistant.",
            },
            {"role": "user", "content": prompt},
        ]

        if output_format:
            # Use function calling for structured output
            functions = [
                {
                    "name": "respond",
                    "description": "Provide structured response",
                    "parameters": output_format,
                }
            ]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=functions,
                function_call={"name": "respond"},
            )

            return json.loads(response.choices[0].message.function_call.arguments)
        else:
            # Regular completion
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages
            )

            return response.choices[0].message.content

    async def create_budget_reallocation_chain(
        self,
        campaigns: List[Dict[str, Any]],
        total_budget: float,
        business_goals: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a prompt chain for complex budget reallocation decisions"""

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


# Utility functions for the AI engine
async def create_ai_engine() -> MarketingAIEngine:
    """Factory function to create and initialize the AI engine"""
    return MarketingAIEngine()


async def test_ai_engine():
    """Test function for the AI engine"""
    engine = await create_ai_engine()

    # Test campaign analysis
    test_campaigns = [
        {
            "campaign_id": "camp_001",
            "campaign_name": "Summer Sale 2024",
            "metrics": {
                "impressions": 50000,
                "clicks": 1000,
                "conversions": 50,
                "cost": 500,
                "revenue": 2500,
            },
        }
    ]

    performances = await engine.analyze_campaign_performance(
        campaigns=test_campaigns,
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
    )

    print("Campaign Analysis:", performances)

    # Test optimization suggestions
    suggestions = await engine.generate_optimization_suggestions(
        campaigns=performances, total_budget=10000, optimization_goal="maximize_roi"
    )

    print("Optimization Suggestions:", suggestions)

    # Test ad copy generation
    ad_variants = await engine.create_personalized_ad_copy(
        product_name="Marketing Automation Platform",
        product_description="AI-powered marketing automation that increases ROI by 300%",
        target_audience={
            "age": "25-45",
            "interests": ["marketing", "technology"],
            "job_title": "marketing manager",
        },
        platform="google_ads",
        num_variants=3,
    )

    print("Ad Copy Variants:", ad_variants)


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_ai_engine())
