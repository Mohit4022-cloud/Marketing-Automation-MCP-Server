"""Unified marketing platform client that abstracts away platform differences"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
import logging

from .google_ads import GoogleAdsClient
from .facebook_ads import FacebookAdsClient
from .google_analytics import GoogleAnalyticsClient
from .base import APIError

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    """Supported marketing platforms"""
    GOOGLE_ADS = "google_ads"
    FACEBOOK_ADS = "facebook_ads"
    GOOGLE_ANALYTICS = "google_analytics"
    ALL = "all"


class UnifiedMarketingClient:
    """
    Unified client that provides a consistent interface across all marketing platforms.
    
    This client handles:
    - Platform-specific authentication
    - Metric normalization across platforms
    - Error handling and retries
    - Parallel requests to multiple platforms
    """
    
    def __init__(self):
        self.clients = {
            Platform.GOOGLE_ADS: GoogleAdsClient(),
            Platform.FACEBOOK_ADS: FacebookAdsClient(),
            Platform.GOOGLE_ANALYTICS: GoogleAnalyticsClient()
        }
        self._connected_clients = set()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect_all()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect_all()
    
    async def connect(self, platform: Platform):
        """Connect to a specific platform"""
        if platform == Platform.ALL:
            await self.connect_all()
        else:
            try:
                await self.clients[platform].connect()
                self._connected_clients.add(platform)
                logger.info(f"Connected to {platform.value}")
            except Exception as e:
                logger.error(f"Failed to connect to {platform.value}: {e}")
                raise

    async def connect_platform(self, platform: Platform):
        """Backward-compatible alias for connect()."""
        await self.connect(platform)
    
    async def connect_all(self):
        """Connect to all available platforms"""
        tasks = []
        for platform, client in self.clients.items():
            tasks.append(self._safe_connect(platform, client))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for platform, result in zip(self.clients.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to connect to {platform.value}: {result}")
            else:
                self._connected_clients.add(platform)
    
    async def _safe_connect(self, platform: Platform, client):
        """Safely connect to a platform, catching exceptions"""
        try:
            await client.connect()
            return True
        except Exception as e:
            return e
    
    async def disconnect(self, platform: Platform):
        """Disconnect from a specific platform"""
        if platform == Platform.ALL:
            await self.disconnect_all()
        else:
            await self.clients[platform].disconnect()
            self._connected_clients.discard(platform)
    
    async def disconnect_all(self):
        """Disconnect from all platforms"""
        tasks = []
        for platform in self._connected_clients:
            tasks.append(self.clients[platform].disconnect())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        self._connected_clients.clear()
    
    def is_connected(self, platform: Platform) -> bool:
        """Check if a platform is connected"""
        return platform in self._connected_clients
    
    async def validate_credentials(self, platform: Platform = Platform.ALL) -> Dict[str, bool]:
        """Validate credentials for one or all platforms"""
        results = {}
        
        if platform == Platform.ALL:
            for plat in self.clients:
                if self.is_connected(plat):
                    results[plat.value] = await self.clients[plat].validate_credentials()
                else:
                    results[plat.value] = False
        else:
            if self.is_connected(platform):
                results[platform.value] = await self.clients[platform].validate_credentials()
            else:
                results[platform.value] = False
        
        return results
    
    async def fetch_campaign_performance(
        self,
        campaign_ids: List[str],
        start_date: datetime,
        end_date: datetime,
        metrics: List[str],
        platforms: Union[Platform, List[Platform]] = Platform.ALL
    ) -> Dict[str, Any]:
        """
        Fetch campaign performance data from one or multiple platforms.
        
        Returns aggregated data with platform-specific results.
        """
        if isinstance(platforms, Platform):
            platforms = [platforms] if platforms != Platform.ALL else list(self.clients.keys())
        
        tasks = {}
        for platform in platforms:
            if self.is_connected(platform):
                client = self.clients[platform]
                tasks[platform.value] = client.fetch_campaign_performance(
                    campaign_ids, start_date, end_date, metrics
                )
        
        # Execute all requests in parallel
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Combine results
        combined_results = {
            "query": {
                "campaign_ids": campaign_ids,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "metrics": metrics,
                "platforms": [p.value for p in platforms]
            },
            "results": {},
            "errors": {},
            "summary": {}
        }
        
        for (platform_name, result) in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                combined_results["errors"][platform_name] = str(result)
            else:
                combined_results["results"][platform_name] = result
        
        # Calculate cross-platform summary
        combined_results["summary"] = self._calculate_summary(combined_results["results"], metrics)
        
        return combined_results
    
    def _calculate_summary(self, platform_results: Dict[str, Any], metrics: List[str]) -> Dict[str, Any]:
        """Calculate summary statistics across all platforms"""
        summary = {
            "total_campaigns": set(),
            "combined_metrics": {metric: 0 for metric in metrics},
            "by_platform": {}
        }
        
        for platform, result in platform_results.items():
            if "data" in result:
                platform_metrics = {metric: 0 for metric in metrics}
                
                for row in result["data"]:
                    summary["total_campaigns"].add(row["campaign_id"])
                    
                    for metric, value in row.get("metrics", {}).items():
                        if metric in metrics:
                            platform_metrics[metric] += value
                            summary["combined_metrics"][metric] += value
                
                summary["by_platform"][platform] = platform_metrics
        
        summary["total_campaigns"] = len(summary["total_campaigns"])
        
        # Calculate derived metrics
        if "clicks" in summary["combined_metrics"] and "impressions" in summary["combined_metrics"]:
            impressions = summary["combined_metrics"]["impressions"]
            if impressions > 0:
                summary["combined_metrics"]["ctr"] = (summary["combined_metrics"]["clicks"] / impressions) * 100
        
        return summary
    
    async def update_campaign_budget(
        self,
        campaign_id: str,
        new_budget: float,
        budget_type: str = "daily",
        platform: Platform = Platform.GOOGLE_ADS
    ) -> Dict[str, Any]:
        """Update campaign budget on a specific platform"""
        if not self.is_connected(platform):
            raise APIError(f"Not connected to {platform.value}")
        
        if platform == Platform.GOOGLE_ANALYTICS:
            return {
                "error": "Google Analytics does not support budget updates",
                "platform": platform.value
            }
        
        return await self.clients[platform].update_campaign_budget(
            campaign_id, new_budget, budget_type
        )
    
    async def pause_campaigns(
        self,
        campaign_ids: List[str],
        platforms: Union[Platform, List[Platform]] = Platform.ALL
    ) -> Dict[str, Any]:
        """Pause campaigns across one or multiple platforms"""
        if isinstance(platforms, Platform):
            platforms = [platforms] if platforms != Platform.ALL else [Platform.GOOGLE_ADS, Platform.FACEBOOK_ADS]
        
        tasks = {}
        for platform in platforms:
            if self.is_connected(platform) and platform != Platform.GOOGLE_ANALYTICS:
                for campaign_id in campaign_ids:
                    key = f"{platform.value}:{campaign_id}"
                    tasks[key] = self.clients[platform].pause_campaign(campaign_id)
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return {
            "paused": {k: v for k, v in zip(tasks.keys(), results) if not isinstance(v, Exception)},
            "errors": {k: str(v) for k, v in zip(tasks.keys(), results) if isinstance(v, Exception)}
        }
    
    async def start_campaigns(
        self,
        campaign_ids: List[str],
        platforms: Union[Platform, List[Platform]] = Platform.ALL
    ) -> Dict[str, Any]:
        """Start/resume campaigns across one or multiple platforms"""
        if isinstance(platforms, Platform):
            platforms = [platforms] if platforms != Platform.ALL else [Platform.GOOGLE_ADS, Platform.FACEBOOK_ADS]
        
        tasks = {}
        for platform in platforms:
            if self.is_connected(platform) and platform != Platform.GOOGLE_ANALYTICS:
                for campaign_id in campaign_ids:
                    key = f"{platform.value}:{campaign_id}"
                    tasks[key] = self.clients[platform].start_campaign(campaign_id)
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return {
            "started": {k: v for k, v in zip(tasks.keys(), results) if not isinstance(v, Exception)},
            "errors": {k: str(v) for k, v in zip(tasks.keys(), results) if isinstance(v, Exception)}
        }
    
    async def get_audience_insights(
        self,
        audience_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        platforms: Union[Platform, List[Platform]] = Platform.ALL
    ) -> Dict[str, Any]:
        """Get audience insights from one or multiple platforms"""
        if isinstance(platforms, Platform):
            platforms = [platforms] if platforms != Platform.ALL else list(self.clients.keys())
        
        tasks = {}
        for platform in platforms:
            if self.is_connected(platform):
                tasks[platform.value] = self.clients[platform].get_audience_insights(
                    audience_id, filters
                )
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        combined_results = {
            "query": {
                "audience_id": audience_id,
                "filters": filters,
                "platforms": [p.value for p in platforms]
            },
            "results": {},
            "errors": {},
            "combined_insights": {}
        }
        
        for (platform_name, result) in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                combined_results["errors"][platform_name] = str(result)
            else:
                combined_results["results"][platform_name] = result
        
        # Combine insights across platforms
        combined_results["combined_insights"] = self._combine_audience_insights(
            combined_results["results"]
        )
        
        return combined_results
    
    def _combine_audience_insights(self, platform_results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine audience insights from multiple platforms"""
        combined = {
            "total_audiences": 0,
            "total_audience_size": 0,
            "demographics": {
                "age_distribution": {},
                "gender_distribution": {},
                "location_distribution": {}
            },
            "interests": [],
            "behaviors": []
        }
        
        for platform, result in platform_results.items():
            if "audiences" in result:
                combined["total_audiences"] += len(result["audiences"])
                for audience in result["audiences"]:
                    combined["total_audience_size"] += audience.get("size", 0)
            
            # Aggregate demographic data
            if "demographic_insights" in result:
                demo = result["demographic_insights"]
                
                # Age distribution
                if "age_distribution" in demo:
                    for age_range, data in demo["age_distribution"].items():
                        if age_range not in combined["demographics"]["age_distribution"]:
                            combined["demographics"]["age_distribution"][age_range] = 0
                        combined["demographics"]["age_distribution"][age_range] += data.get("users", data)
                
                # Gender distribution
                if "gender_distribution" in demo:
                    for gender, data in demo["gender_distribution"].items():
                        if gender not in combined["demographics"]["gender_distribution"]:
                            combined["demographics"]["gender_distribution"][gender] = 0
                        combined["demographics"]["gender_distribution"][gender] += data.get("users", data)
            
            # Collect interests
            if "interest_insights" in result and "available_interests" in result["interest_insights"]:
                combined["interests"].extend(result["interest_insights"]["available_interests"])
        
        return combined
    
    async def get_platform_status(self) -> Dict[str, Any]:
        """Get the connection status and health of all platforms"""
        status = {
            "connected_platforms": [p.value for p in self._connected_clients],
            "platform_details": {}
        }
        
        for platform in self.clients:
            platform_status = {
                "connected": self.is_connected(platform),
                "authenticated": False,
                "rate_limit_status": "unknown"
            }
            
            if self.is_connected(platform):
                try:
                    platform_status["authenticated"] = await self.clients[platform].validate_credentials()
                    # Get rate limit info
                    rate_limiter = self.clients[platform].rate_limiter
                    platform_status["rate_limit_status"] = {
                        "requests_last_minute": len(rate_limiter.minute_bucket),
                        "requests_last_hour": len(rate_limiter.hour_bucket),
                        "requests_last_day": len(rate_limiter.day_bucket)
                    }
                except Exception as e:
                    platform_status["error"] = str(e)
            
            status["platform_details"][platform.value] = platform_status
        
        return status
