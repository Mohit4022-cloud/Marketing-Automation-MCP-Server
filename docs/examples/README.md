# Example Workflows

These examples are limited to interfaces that exist in the repo today.

## 1. CLI Smoke Flow

Use the installed CLI for a deterministic local pass:

```bash
uv run marketing-automation report --campaign-ids camp_001 --campaign-ids camp_002
uv run marketing-automation optimize --campaign-ids camp_001 --campaign-ids camp_002 --budget 5000
uv run marketing-automation copy --product "Marketing OS" --description "Turns campaign data into actions" --audience "Marketing leaders"
uv run marketing-automation segment
```

## 2. Direct Python Tool Call

You can call the tool functions directly for local testing:

```python
import asyncio

from src.models import GenerateCampaignReportInput, MetricType
from src.tools.marketing_tools import generate_campaign_report


async def main():
    result = await generate_campaign_report(
        GenerateCampaignReportInput(
            campaign_ids=["camp_001", "camp_002"],
            date_range={"start": "2024-01-01", "end": "2024-01-31"},
            metrics=[
                MetricType.IMPRESSIONS,
                MetricType.CLICKS,
                MetricType.CONVERSIONS,
                MetricType.COST,
                MetricType.REVENUE,
            ],
        )
    )

    print(result.status)
    print(result.mode)
    print(result.summary)


asyncio.run(main())
```

## 3. Expected Live-Mode Block

The repo is designed to block honestly when a live dependency is missing.

```python
import asyncio

from src.models import CreateCampaignCopyInput, ToneOfVoice
from src.tools.marketing_tools import create_campaign_copy


async def main():
    result = await create_campaign_copy(
        CreateCampaignCopyInput(
            product_name="Marketing OS",
            product_description="Turns campaign data into actions",
            target_audience="Marketing leaders",
            tone=ToneOfVoice.PROFESSIONAL,
            copy_type="ad_headline",
        )
    )

    print(result.status)
    print(result.blocked_reason)


asyncio.run(main())
```

If the selected provider is not configured in live mode, the result should be:
- `status = "blocked"`
- `mode = "live"`
- `blocked_reason` explaining what is missing

## 4. MCP Payload Example

Current payload for `create_campaign_copy`:

```json
{
  "product_name": "Marketing OS",
  "product_description": "Turns campaign data into actions",
  "target_audience": "Marketing leaders",
  "tone": "professional",
  "copy_type": "ad_headline",
  "variants_count": 3,
  "keywords": ["automation", "roi"],
  "max_length": 120
}
```

Current response fields to rely on:
- `copy_generation_id`
- `variants`
- `best_variant_id`
- `generation_metadata`

Do not rely on stale fields from older docs such as `best_performer_index`.

## 5. Unified Client Example

The unified client is useful for integration testing and internal aggregation:

```python
import asyncio
from datetime import datetime

from src.integrations.unified_client import Platform, UnifiedMarketingClient


async def main():
    client = UnifiedMarketingClient()
    client._connected_clients = {Platform.GOOGLE_ADS}
    client.clients[Platform.GOOGLE_ADS] = ...  # replace with a stub or AsyncMock in tests

    result = await client.fetch_campaign_performance(
        campaign_ids=["camp_001"],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        metrics=["clicks", "impressions"],
        platforms=[Platform.GOOGLE_ADS],
    )
    print(result["summary"])


asyncio.run(main())
```

For real behavior, prefer the tested contract under [docs/api/README.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/api/README.md).
