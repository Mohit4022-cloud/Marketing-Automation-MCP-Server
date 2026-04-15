# Operator Runbook

## Local Bootstrap

Preferred path:

```bash
uv sync --python 3.13 --extra dev
cp .env.example .env
uv run python -m compileall src tests dashboard
uv run pytest
```

Supported Python versions:
- `3.12`
- `3.13`

Do not treat local `3.14.x` as the supported baseline for this repo yet.

## Demo Validation

Set `DEMO_MODE=true` and run:

```bash
uv run marketing-automation report --campaign-ids camp_001 --campaign-ids camp_002
uv run marketing-automation optimize --campaign-ids camp_001 --campaign-ids camp_002 --budget 5000
uv run marketing-automation copy --product "Marketing OS" --description "Turns campaign data into actions" --audience "Marketing leaders"
uv run marketing-automation segment
```

Expected demo behavior:
- `status="ok"`
- `mode="demo"`
- deterministic outputs for repeated inputs

## Live-Mode Blocked Behavior

Set `DEMO_MODE=false`.

Expected blocked cases:
- `generate_campaign_report`
  Blocks if no live platform credentials are configured.
- `optimize_campaign_budget`
  Blocks if no live platform credentials are configured or if no AI provider is configured.
- `create_campaign_copy`
  Blocks if the selected AI provider is not configured.
- `analyze_audience_segments`
  Always blocks in live mode in the current repo because no live contact source is wired.

Every blocked response should include:
- `status`
- `mode`
- `blocked_reason`
- `warnings`

## Expected Credentials

OpenAI:
- `AI_PROVIDER=openai`
- `OPENAI_API_KEY`
- `AI_OPENAI_MODEL`

Anthropic:
- `AI_PROVIDER=anthropic`
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`

Gemini:
- `AI_PROVIDER=gemini`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

Google Ads:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`
- `GOOGLE_ADS_CUSTOMER_ID`

Facebook Ads:
- `FACEBOOK_APP_ID`
- `FACEBOOK_APP_SECRET`
- `FACEBOOK_ACCESS_TOKEN`

Google Analytics:
- `GOOGLE_ANALYTICS_PROPERTY_ID`
- either OAuth client credentials plus refresh token, or `GOOGLE_ANALYTICS_SERVICE_ACCOUNT_PATH`

## Security Defaults

For stable live behavior, set:
- `SECRET_KEY`
- `ENCRYPTION_KEY`

If `SECRET_KEY` is not set, token-based helpers should be treated as unavailable.
If `ENCRYPTION_KEY` is not set, API-key encryption is disabled for that process and the server logs a warning.

## Container Validation

```bash
docker build -t marketing-automation-mcp:latest .
docker run --rm -e DEMO_MODE=true marketing-automation-mcp:latest python -m compileall src tests dashboard
docker run --rm -e DEMO_MODE=true marketing-automation-mcp:latest python -c "import src.server, src.cli, src.ai_engine, src.performance; print('imports ok')"
```
