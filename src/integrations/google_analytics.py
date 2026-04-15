"""Google Analytics API client implementation"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import UTC, datetime, timedelta
import logging
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from .base import (
    BaseIntegrationClient,
    RateLimitConfig,
    APIError,
    AuthenticationError,
    rate_limited,
    retry_on_error,
)

logger = logging.getLogger(__name__)


class GoogleAnalyticsClient(BaseIntegrationClient):
    """Google Analytics Data API (GA4) client with authentication and rate limiting"""

    API_VERSION = "v1beta"
    BASE_URL = "https://analyticsdata.googleapis.com"

    def __init__(self):
        # Google Analytics has generous rate limits
        rate_config = RateLimitConfig(
            requests_per_minute=120, requests_per_hour=3600, requests_per_day=50000
        )
        super().__init__(rate_config)

        # Load credentials from environment
        self.property_id = os.getenv("GOOGLE_ANALYTICS_PROPERTY_ID")
        self.service_account_path = os.getenv("GOOGLE_ANALYTICS_SERVICE_ACCOUNT_PATH")

        # OAuth2 credentials (alternative to service account)
        self.client_id = os.getenv("GOOGLE_ANALYTICS_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_ANALYTICS_CLIENT_SECRET")
        self.refresh_token = os.getenv("GOOGLE_ANALYTICS_REFRESH_TOKEN")

        self._credentials = None
        self._access_token = None

    async def authenticate(self):
        """Authenticate with Google Analytics API"""
        if not self.property_id:
            raise AuthenticationError("Missing Google Analytics property ID")

        # Prefer service account authentication
        if self.service_account_path and os.path.exists(self.service_account_path):
            await self._authenticate_service_account()
        elif all([self.client_id, self.client_secret, self.refresh_token]):
            await self._authenticate_oauth()
        else:
            raise AuthenticationError(
                "No valid authentication method found for Google Analytics"
            )

        self._authenticated = True

    async def _authenticate_service_account(self):
        """Authenticate using service account"""
        try:
            self._credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            self._credentials.refresh(Request())
            self._access_token = self._credentials.token
        except Exception as e:
            raise AuthenticationError(f"Service account authentication failed: {e}")

    async def _authenticate_oauth(self):
        """Authenticate using OAuth2 refresh token"""
        token_url = "https://oauth2.googleapis.com/token"

        response = await self._client.post(
            token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )

        if response.status_code != 200:
            raise AuthenticationError(f"OAuth2 token refresh failed: {response.text}")

        token_data = response.json()
        self._access_token = token_data["access_token"]

    async def validate_credentials(self) -> bool:
        """Validate Google Analytics credentials"""
        try:
            # Try to fetch property metadata
            url = f"{self.BASE_URL}/{self.API_VERSION}/properties/{self.property_id}/metadata"
            headers = {"Authorization": f"Bearer {self._access_token}"}

            response = await self._make_request("GET", url, headers=headers)
            return "dimensions" in response
        except Exception as e:
            logger.error(f"Google Analytics credential validation failed: {e}")
            return False

    @rate_limited
    @retry_on_error()
    async def fetch_campaign_performance(
        self,
        campaign_ids: List[str],
        start_date: datetime,
        end_date: datetime,
        metrics: List[str],
    ) -> Dict[str, Any]:
        """Fetch campaign performance data from Google Analytics"""

        # Map generic metrics to GA4 metrics
        metric_mapping = {
            "sessions": "sessions",
            "users": "totalUsers",
            "new_users": "newUsers",
            "page_views": "screenPageViews",
            "bounce_rate": "bounceRate",
            "avg_session_duration": "averageSessionDuration",
            "conversions": "conversions",
            "conversion_rate": "sessionConversionRate",
            "revenue": "totalRevenue",
            "engagement_rate": "engagementRate",
        }

        ga_metrics = []
        for metric in metrics:
            ga_metric = metric_mapping.get(metric, metric)
            ga_metrics.append({"name": ga_metric})

        # Build request body
        request_body = {
            "dateRanges": [
                {
                    "startDate": start_date.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d"),
                }
            ],
            "dimensions": [
                {"name": "campaignId"},
                {"name": "campaignName"},
                {"name": "date"},
            ],
            "metrics": ga_metrics,
            "dimensionFilter": (
                {
                    "filter": {
                        "fieldName": "campaignId",
                        "inListFilter": {"values": campaign_ids},
                    }
                }
                if campaign_ids
                else None
            ),
            "limit": 10000,
        }

        # Remove None filter if no campaign IDs specified
        if not campaign_ids:
            request_body.pop("dimensionFilter", None)

        url = f"{self.BASE_URL}/{self.API_VERSION}/properties/{self.property_id}:runReport"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        response = await self._make_request(
            "POST", url, headers=headers, json_data=request_body
        )

        # Parse response
        results = []
        for row in response.get("rows", []):
            dimension_values = row.get("dimensionValues", [])
            metric_values = row.get("metricValues", [])

            result = {
                "campaign_id": (
                    dimension_values[0].get("value")
                    if len(dimension_values) > 0
                    else "unknown"
                ),
                "campaign_name": (
                    dimension_values[1].get("value")
                    if len(dimension_values) > 1
                    else "unknown"
                ),
                "date": (
                    dimension_values[2].get("value")
                    if len(dimension_values) > 2
                    else "unknown"
                ),
                "metrics": {},
            }

            # Extract metrics
            for i, metric in enumerate(metrics):
                if i < len(metric_values):
                    value = metric_values[i].get("value", "0")
                    # Convert to appropriate type
                    try:
                        if "rate" in metric or metric in [
                            "bounce_rate",
                            "conversion_rate",
                        ]:
                            result["metrics"][metric] = float(value)
                        elif metric in ["revenue"]:
                            result["metrics"][metric] = float(value)
                        else:
                            result["metrics"][metric] = int(float(value))
                    except ValueError:
                        result["metrics"][metric] = 0

            results.append(result)

        return {
            "platform": "google_analytics",
            "data": results,
            "total_results": len(results),
            "property_id": self.property_id,
            "query_date": datetime.utcnow().isoformat(),
        }

    @rate_limited
    @retry_on_error()
    async def update_campaign_budget(
        self, campaign_id: str, new_budget: float, budget_type: str = "daily"
    ) -> Dict[str, Any]:
        """Google Analytics doesn't manage campaign budgets - this is informational only"""

        logger.warning(
            "Google Analytics cannot update campaign budgets. Use Google Ads or Facebook Ads APIs."
        )

        return {
            "platform": "google_analytics",
            "campaign_id": campaign_id,
            "status": "not_supported",
            "message": "Google Analytics is a read-only analytics platform. Use the advertising platform's API to update budgets.",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Google Analytics doesn't manage campaign status"""
        return {
            "platform": "google_analytics",
            "campaign_id": campaign_id,
            "status": "not_supported",
            "message": "Google Analytics cannot pause campaigns. Use the advertising platform's API.",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def start_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Google Analytics doesn't manage campaign status"""
        return {
            "platform": "google_analytics",
            "campaign_id": campaign_id,
            "status": "not_supported",
            "message": "Google Analytics cannot start campaigns. Use the advertising platform's API.",
            "timestamp": datetime.utcnow().isoformat(),
        }

    @rate_limited
    @retry_on_error()
    async def get_audience_insights(
        self,
        audience_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get audience insights from Google Analytics"""

        # Build dimensions and metrics for audience analysis
        dimensions = [
            {"name": "country"},
            {"name": "city"},
            {"name": "deviceCategory"},
            {"name": "operatingSystem"},
            {"name": "browser"},
            {"name": "languageCode"},
        ]

        # Add demographic dimensions if available
        if filters and filters.get("include_demographics"):
            dimensions.extend([{"name": "userAgeBracket"}, {"name": "userGender"}])

        metrics = [
            {"name": "totalUsers"},
            {"name": "newUsers"},
            {"name": "sessions"},
            {"name": "engagementRate"},
            {"name": "averageSessionDuration"},
            {"name": "screenPageViewsPerSession"},
        ]

        # Date range for last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        request_body = {
            "dateRanges": [
                {
                    "startDate": start_date.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d"),
                }
            ],
            "dimensions": dimensions,
            "metrics": metrics,
            "limit": 1000,
        }

        # Add audience segment filter if provided
        if audience_id:
            request_body["dimensionFilter"] = {
                "filter": {
                    "fieldName": "audienceId",
                    "stringFilter": {"value": audience_id},
                }
            }

        url = f"{self.BASE_URL}/{self.API_VERSION}/properties/{self.property_id}:runReport"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        response = await self._make_request(
            "POST", url, headers=headers, json_data=request_body
        )

        # Aggregate insights by different dimensions
        insights = {
            "platform": "google_analytics",
            "geographic_distribution": {},
            "device_distribution": {},
            "demographic_distribution": {},
            "behavioral_metrics": {},
            "top_segments": [],
        }

        # Process response rows
        for row in response.get("rows", []):
            dimensions_data = {
                dim["name"]: val["value"]
                for dim, val in zip(dimensions, row.get("dimensionValues", []))
            }
            metrics_data = {
                metric["name"]: float(val.get("value", 0))
                for metric, val in zip(metrics, row.get("metricValues", []))
            }

            # Aggregate by country
            country = dimensions_data.get("country", "Unknown")
            if country not in insights["geographic_distribution"]:
                insights["geographic_distribution"][country] = {
                    "users": 0,
                    "sessions": 0,
                    "engagement_rate": 0,
                }
            insights["geographic_distribution"][country]["users"] += metrics_data.get(
                "totalUsers", 0
            )
            insights["geographic_distribution"][country][
                "sessions"
            ] += metrics_data.get("sessions", 0)

            # Aggregate by device
            device = dimensions_data.get("deviceCategory", "Unknown")
            if device not in insights["device_distribution"]:
                insights["device_distribution"][device] = {"users": 0, "sessions": 0}
            insights["device_distribution"][device]["users"] += metrics_data.get(
                "totalUsers", 0
            )
            insights["device_distribution"][device]["sessions"] += metrics_data.get(
                "sessions", 0
            )

            # Aggregate demographics if available
            if "userAgeBracket" in dimensions_data:
                age_bracket = dimensions_data["userAgeBracket"]
                gender = dimensions_data.get("userGender", "unknown")

                if "age_distribution" not in insights["demographic_distribution"]:
                    insights["demographic_distribution"]["age_distribution"] = {}
                if "gender_distribution" not in insights["demographic_distribution"]:
                    insights["demographic_distribution"]["gender_distribution"] = {}

                if (
                    age_bracket
                    not in insights["demographic_distribution"]["age_distribution"]
                ):
                    insights["demographic_distribution"]["age_distribution"][
                        age_bracket
                    ] = 0
                insights["demographic_distribution"]["age_distribution"][
                    age_bracket
                ] += metrics_data.get("totalUsers", 0)

                if (
                    gender
                    not in insights["demographic_distribution"]["gender_distribution"]
                ):
                    insights["demographic_distribution"]["gender_distribution"][
                        gender
                    ] = 0
                insights["demographic_distribution"]["gender_distribution"][
                    gender
                ] += metrics_data.get("totalUsers", 0)

        # Calculate overall behavioral metrics
        total_users = sum(
            row.get("metricValues", [{}])[0].get("value", 0)
            for row in response.get("rows", [])
        )

        insights["behavioral_metrics"] = {
            "total_users": total_users,
            "avg_engagement_rate": (
                response.get("totals", [{}])[3].get("value", 0)
                if len(response.get("totals", [])) > 3
                else 0
            ),
            "avg_session_duration": (
                response.get("totals", [{}])[4].get("value", 0)
                if len(response.get("totals", [])) > 4
                else 0
            ),
        }

        # Get top performing segments
        if filters and filters.get("segment_by"):
            segment_dimension = filters["segment_by"]
            # Additional segmentation logic here

        insights["property_id"] = self.property_id
        insights["date_range"] = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        }
        insights["retrieved_at"] = datetime.utcnow().isoformat()

        return insights
