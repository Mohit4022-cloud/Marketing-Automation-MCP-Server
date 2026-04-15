# Quick Start

This guide is for the current repo shape on April 15, 2026.

## Prerequisites

- Python `3.12` or `3.13`
- `uv`
- Optional live credentials for ad platforms and AI providers

## 1. Bootstrap

```bash
uv sync --python 3.13 --extra dev
cp .env.example .env
```

If you stay in demo mode, no external credentials are required.

## 2. Validate The Environment

```bash
uv run python -m compileall src tests dashboard
uv run pytest
uv run python -c "import src.server, src.cli, src.ai_engine, src.performance; print('imports ok')"
```

## 3. Start The MCP Server

```bash
uv run python -m src.server
```

The supported transport for this repo is `stdio`.

## 4. Demo Mode

Set:

```bash
DEMO_MODE=true
```

Demo mode behavior:
- responses are deterministic
- no provider credentials are required
- audience segmentation is available

CLI smoke examples:

```bash
uv run marketing-automation report --campaign-ids camp_001 --campaign-ids camp_002
uv run marketing-automation optimize --campaign-ids camp_001 --campaign-ids camp_002 --budget 5000
uv run marketing-automation copy --product "Marketing OS" --description "Turns campaign data into actions" --audience "Marketing leaders"
uv run marketing-automation segment
```

## 5. Live Mode

Set:

```bash
DEMO_MODE=false
AI_PROVIDER=openai
OPENAI_API_KEY=...
AI_OPENAI_MODEL=gpt-5.4
```

Add at least one platform credential set if you want live reporting or optimization:
- Google Ads
- Facebook Ads
- Google Analytics

Live mode behavior:
- report and optimize require at least one configured marketing platform
- copy requires the selected AI provider to be configured
- audience segmentation returns `status="blocked"` because no live contact source is wired in this repo

## 6. MCP Payload Examples

Generate a report:

```json
{
  "campaign_ids": ["camp_001", "camp_002"],
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "metrics": ["impressions", "clicks", "conversions", "cost", "revenue", "roi"],
  "format": "json",
  "include_charts": true,
  "group_by": "campaign"
}
```

Create campaign copy:

```json
{
  "product_name": "Marketing OS",
  "product_description": "Turns campaign data into actions",
  "target_audience": "Marketing leaders",
  "tone": "professional",
  "copy_type": "ad_headline",
  "variants_count": 3,
  "keywords": ["automation", "roi"]
}
```

The current copy response uses `best_variant_id`. Older docs that referenced `best_performer_index` are stale.

## 7. Claude Desktop Configuration

```json
{
  "mcpServers": {
    "marketing-automation": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.server"],
      "cwd": "/absolute/path/to/Marketing-Automation-MCP-Server"
    }
  }
}
```

## 8. What To Read Next

- [API Reference](./api/README.md)
- [Example Workflows](./examples/README.md)
- [Operator Runbook](./operator-runbook.md)
- [System Audit Review Docs](./reviews/README.md)
