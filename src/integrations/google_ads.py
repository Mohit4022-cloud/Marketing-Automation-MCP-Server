"""Google Ads API client implementation"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from .base import (
    BaseIntegrationClient,
    RateLimitConfig,
    APIError,
    AuthenticationError,
    rate_limited,
    retry_on_error
)

logger = logging.getLogger(__name__)


class GoogleAdsClient(BaseIntegrationClient):
    """Google Ads API client with authentication and rate limiting"""
    
    API_VERSION = "v15"
    BASE_URL = "https://googleads.googleapis.com"
    
    def __init__(self):
        # Google Ads has strict rate limits
        rate_config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=900,
            requests_per_day=15000
        )
        super().__init__(rate_config)
        
        # Load credentials from environment
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        self.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
        self.refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
        self.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
        self.login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", self.customer_id)
        
        # For service account authentication (optional)
        self.service_account_path = os.getenv("GOOGLE_ADS_SERVICE_ACCOUNT_PATH")
        
        self._access_token = None
        self._token_expiry = None
    
    async def authenticate(self):
        """Authenticate with Google Ads API"""
        if not all([self.developer_token, self.customer_id]):
            raise AuthenticationError("Missing required Google Ads credentials")
        
        # Use service account if available
        if self.service_account_path and os.path.exists(self.service_account_path):
            await self._authenticate_service_account()
        else:
            await self._authenticate_oauth()
        
        self._authenticated = True
    
    async def _authenticate_service_account(self):
        """Authenticate using service account"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=["https://www.googleapis.com/auth/adwords"]
            )
            credentials.refresh(Request())
            self._access_token = credentials.token
            self._token_expiry = credentials.expiry
        except Exception as e:
            raise AuthenticationError(f"Service account authentication failed: {e}")
    
    async def _authenticate_oauth(self):
        """Authenticate using OAuth2 refresh token"""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise AuthenticationError("Missing OAuth2 credentials for Google Ads")
        
        token_url = "https://oauth2.googleapis.com/token"
        
        response = await self._client.post(
            token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }
        )
        
        if response.status_code != 200:
            raise AuthenticationError(f"OAuth2 token refresh failed: {response.text}")
        
        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._token_expiry = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
    
    async def validate_credentials(self) -> bool:
        """Validate Google Ads credentials"""
        try:
            # Try to fetch account info
            url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}"
            headers = self._get_headers()
            
            response = await self._make_request("GET", url, headers=headers)
            return True
        except Exception as e:
            logger.error(f"Google Ads credential validation failed: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "developer-token": self.developer_token,
            "login-customer-id": self.login_customer_id,
            "Content-Type": "application/json"
        }
    
    @rate_limited
    @retry_on_error()
    async def fetch_campaign_performance(
        self,
        campaign_ids: List[str],
        start_date: datetime,
        end_date: datetime,
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Fetch campaign performance data from Google Ads"""
        
        # Map generic metrics to Google Ads metrics
        metric_mapping = {
            "impressions": "metrics.impressions",
            "clicks": "metrics.clicks",
            "conversions": "metrics.conversions",
            "cost": "metrics.cost_micros",
            "ctr": "metrics.ctr",
            "conversion_rate": "metrics.conversion_rate",
            "average_cpc": "metrics.average_cpc"
        }
        
        google_metrics = [metric_mapping.get(m, f"metrics.{m}") for m in metrics]
        
        # Build Google Ads Query Language (GAQL) query
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                segments.date,
                {', '.join(google_metrics)}
            FROM campaign
            WHERE
                campaign.id IN ({', '.join(campaign_ids)})
                AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' 
                AND '{end_date.strftime('%Y-%m-%d')}'
            ORDER BY segments.date DESC
        """
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/googleAds:searchStream"
        headers = self._get_headers()
        
        response = await self._make_request(
            "POST",
            url,
            headers=headers,
            json_data={"query": query}
        )
        
        # Parse response. Google Ads searchStream may return either a list of batches
        # or a flattened results payload in mocked/local environments.
        results = []
        response_batches = response.get("results", [])
        if response_batches and isinstance(response_batches[0], dict) and "campaign" in response_batches[0]:
            response_batches = [{"results": response_batches}]

        for batch in response_batches:
            for row in batch.get("results", []):
                result = {
                    "campaign_id": row["campaign"]["id"],
                    "campaign_name": row["campaign"]["name"],
                    "date": row["segments"]["date"],
                    "metrics": {}
                }
                
                # Extract metrics
                for metric in metrics:
                    google_metric = metric_mapping.get(metric, f"metrics.{metric}")
                    metric_path = google_metric.split(".")
                    value = row
                    for part in metric_path:
                        value = value.get(part, 0)
                    
                    # Convert micros to currency for cost metrics
                    if "cost" in metric or "cpc" in metric:
                        value = value / 1_000_000
                    
                    result["metrics"][metric] = value
                
                results.append(result)
        
        return {
            "platform": "google_ads",
            "data": results,
            "total_results": len(results),
            "query_date": datetime.utcnow().isoformat()
        }
    
    @rate_limited
    @retry_on_error()
    async def update_campaign_budget(
        self,
        campaign_id: str,
        new_budget: float,
        budget_type: str = "daily"
    ) -> Dict[str, Any]:
        """Update campaign budget in Google Ads"""
        
        # First, get the campaign budget ID
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign_budget.id,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/googleAds:search"
        headers = self._get_headers()
        
        response = await self._make_request(
            "POST",
            url,
            headers=headers,
            json_data={"query": query}
        )
        
        if not response.get("results"):
            raise APIError(f"Campaign {campaign_id} not found")
        
        budget_id = response["results"][0]["campaignBudget"]["id"]
        
        # Update the budget
        budget_micros = int(new_budget * 1_000_000)
        
        operations = [{
            "update": {
                "resource_name": f"customers/{self.customer_id}/campaignBudgets/{budget_id}",
                "amount_micros": budget_micros
            },
            "update_mask": "amount_micros"
        }]
        
        mutate_url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/campaignBudgets:mutate"
        
        mutate_response = await self._make_request(
            "POST",
            mutate_url,
            headers=headers,
            json_data={"operations": operations}
        )
        
        return {
            "platform": "google_ads",
            "campaign_id": campaign_id,
            "budget_id": budget_id,
            "new_budget": new_budget,
            "budget_type": budget_type,
            "status": "updated",
            "updated_at": datetime.utcnow().isoformat()
        }
    
    @rate_limited
    @retry_on_error()
    async def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pause a Google Ads campaign"""
        return await self._update_campaign_status(campaign_id, "PAUSED")
    
    @rate_limited
    @retry_on_error()
    async def start_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Start/resume a Google Ads campaign"""
        return await self._update_campaign_status(campaign_id, "ENABLED")
    
    async def _update_campaign_status(self, campaign_id: str, status: str) -> Dict[str, Any]:
        """Update campaign status"""
        operations = [{
            "update": {
                "resource_name": f"customers/{self.customer_id}/campaigns/{campaign_id}",
                "status": status
            },
            "update_mask": "status"
        }]
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/campaigns:mutate"
        headers = self._get_headers()
        
        response = await self._make_request(
            "POST",
            url,
            headers=headers,
            json_data={"operations": operations}
        )
        
        return {
            "platform": "google_ads",
            "campaign_id": campaign_id,
            "status": status.lower(),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    @rate_limited
    @retry_on_error()
    async def get_audience_insights(
        self,
        audience_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get audience insights from Google Ads"""
        
        # Build query for audience insights
        query = """
            SELECT
                audience.id,
                audience.name,
                audience.description,
                audience.status,
                audience.size_for_display,
                audience.size_for_search,
                user_list.size_for_display,
                user_list.size_for_search,
                user_list.eligible_for_display,
                user_list.eligible_for_search
            FROM audience
        """
        
        if audience_id:
            query += f" WHERE audience.id = {audience_id}"
        
        query += " LIMIT 100"
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/googleAds:search"
        headers = self._get_headers()
        
        response = await self._make_request(
            "POST",
            url,
            headers=headers,
            json_data={"query": query}
        )
        
        audiences = []
        for result in response.get("results", []):
            audience_data = result.get("audience", {})
            user_list = result.get("userList", {})
            
            audiences.append({
                "id": audience_data.get("id"),
                "name": audience_data.get("name"),
                "description": audience_data.get("description"),
                "status": audience_data.get("status"),
                "size_display": user_list.get("sizeForDisplay", 0),
                "size_search": user_list.get("sizeForSearch", 0),
                "eligible_display": user_list.get("eligibleForDisplay", False),
                "eligible_search": user_list.get("eligibleForSearch", False)
            })
        
        # Get demographic insights if filters are provided
        demographic_insights = {}
        if filters and filters.get("include_demographics"):
            demographic_query = """
                SELECT
                    campaign.id,
                    ad_group.id,
                    segments.demographic_age_range,
                    segments.demographic_gender,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.conversions
                FROM ad_group
                WHERE segments.date DURING LAST_30_DAYS
                LIMIT 1000
            """
            
            demo_response = await self._make_request(
                "POST",
                url,
                headers=headers,
                json_data={"query": demographic_query}
            )
            
            # Aggregate demographic data
            age_data = {}
            gender_data = {}
            
            for result in demo_response.get("results", []):
                segments = result.get("segments", {})
                metrics = result.get("metrics", {})
                
                age_range = segments.get("demographicAgeRange", "UNKNOWN")
                gender = segments.get("demographicGender", "UNKNOWN")
                
                if age_range != "UNKNOWN":
                    if age_range not in age_data:
                        age_data[age_range] = {"impressions": 0, "clicks": 0, "conversions": 0}
                    age_data[age_range]["impressions"] += metrics.get("impressions", 0)
                    age_data[age_range]["clicks"] += metrics.get("clicks", 0)
                    age_data[age_range]["conversions"] += metrics.get("conversions", 0)
                
                if gender != "UNKNOWN":
                    if gender not in gender_data:
                        gender_data[gender] = {"impressions": 0, "clicks": 0, "conversions": 0}
                    gender_data[gender]["impressions"] += metrics.get("impressions", 0)
                    gender_data[gender]["clicks"] += metrics.get("clicks", 0)
                    gender_data[gender]["conversions"] += metrics.get("conversions", 0)
            
            demographic_insights = {
                "age_distribution": age_data,
                "gender_distribution": gender_data
            }
        
        return {
            "platform": "google_ads",
            "audiences": audiences,
            "total_audiences": len(audiences),
            "demographic_insights": demographic_insights,
            "retrieved_at": datetime.utcnow().isoformat()
        }
