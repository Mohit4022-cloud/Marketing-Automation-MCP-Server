"""Unit tests for integration clients and aggregation helpers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.integrations.google_ads import GoogleAdsClient
from src.integrations.google_analytics import GoogleAnalyticsClient
from src.integrations.unified_client import Platform, UnifiedMarketingClient


@pytest.mark.asyncio
async def test_google_ads_authentication(monkeypatch, mock_google_ads_client):
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "dev-token")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "1234567890")
    client = GoogleAdsClient()
    await client.connect()
    assert client._authenticated is True
    assert client._access_token == "mock_token"


@pytest.mark.asyncio
async def test_google_analytics_budget_update_is_not_supported():
    client = GoogleAnalyticsClient()
    result = await client.update_campaign_budget("camp_001", 500.0)
    assert result["status"] == "not_supported"


@pytest.mark.asyncio
async def test_unified_client_aggregates_metrics():
    client = UnifiedMarketingClient()
    client._connected_clients = {Platform.GOOGLE_ADS, Platform.FACEBOOK_ADS}
    client.clients[Platform.GOOGLE_ADS] = AsyncMock()
    client.clients[Platform.FACEBOOK_ADS] = AsyncMock()
    client.clients[Platform.GOOGLE_ADS].fetch_campaign_performance.return_value = {
        "platform": "google_ads",
        "data": [
            {"campaign_id": "g_001", "campaign_name": "Google", "metrics": {"clicks": 100, "impressions": 1000}}
        ],
    }
    client.clients[Platform.FACEBOOK_ADS].fetch_campaign_performance.return_value = {
        "platform": "facebook_ads",
        "data": [
            {"campaign_id": "f_001", "campaign_name": "Facebook", "metrics": {"clicks": 50, "impressions": 500}}
        ],
    }
    result = await client.fetch_campaign_performance(
        campaign_ids=["g_001", "f_001"],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        metrics=["clicks", "impressions"],
        platforms=[Platform.GOOGLE_ADS, Platform.FACEBOOK_ADS],
    )
    assert result["summary"]["combined_metrics"]["clicks"] == 150
    assert result["summary"]["combined_metrics"]["impressions"] == 1500
    assert result["summary"]["total_campaigns"] == 2
