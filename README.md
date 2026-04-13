# Marketing Automation MCP Server

Marketing Automation MCP Server is a Python MCP service for campaign reporting, budget optimization, copy generation, and demo-only audience segmentation.

This repo now has two explicit execution modes:

- `DEMO_MODE=true`: deterministic sample outputs for local demos and contract testing
- `DEMO_MODE=false`: live mode that uses configured ad-platform credentials and the selected AI provider

Live mode is intentionally honest. If a required platform or AI provider is not configured, the tool returns a structured `blocked` response instead of fabricating output.

## What Works

- MCP server entrypoint in [src/server.py](/Users/mohit/Marketing-Automation-MCP-Server/src/server.py)
- CLI for local testing in [src/cli.py](/Users/mohit/Marketing-Automation-MCP-Server/src/cli.py)
- Unified marketing platform client in [src/integrations/unified_client.py](/Users/mohit/Marketing-Automation-MCP-Server/src/integrations/unified_client.py)
- Provider-backed AI engine with OpenAI, Anthropic, and Gemini adapters under [src/ai/providers](/Users/mohit/Marketing-Automation-MCP-Server/src/ai/providers)
- SQLAlchemy persistence for campaigns, automation tasks, metrics, and AI decisions in [src/database.py](/Users/mohit/Marketing-Automation-MCP-Server/src/database.py)

## AI Providers

- Default provider: OpenAI with model `gpt-5.4`
- Optional providers: Anthropic and Gemini
- OpenAI uses the Responses API path in the provider adapter
- Anthropic and Gemini are wired through the same `generate_text()` / `generate_structured()` abstraction

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"
```

If you prefer `requirements.txt`:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

## Configure

```bash
cp .env.example .env
```

Minimum useful configurations:

- Demo mode only:
  - `DEMO_MODE=true`
- Live report / optimize:
  - `DEMO_MODE=false`
  - one or more platform credential sets
- Live copy generation:
  - `DEMO_MODE=false`
  - `AI_PROVIDER=openai`
  - `OPENAI_API_KEY=...`
  - `AI_OPENAI_MODEL=gpt-5.4`

Optional provider env vars:

- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`

## Run

Start the MCP server:

```bash
python3 -m src.server
```

Or use the installed CLI entrypoint:

```bash
marketing-automation report --campaign-ids camp_001 --campaign-ids camp_002
marketing-automation optimize --campaign-ids camp_001 --campaign-ids camp_002 --budget 5000
marketing-automation copy --product "Marketing OS" --description "Turns campaign data into actions" --audience "Marketing leaders"
marketing-automation segment
```

## MCP Tools

### `generate_campaign_report`

- Demo mode: deterministic campaign metrics and charts
- Live mode: fetches campaign data from configured ad platforms
- If no live platform credentials are available, returns `status=blocked`

### `optimize_campaign_budget`

- Demo mode: deterministic allocations
- Live mode: uses platform metrics plus the configured AI provider
- Persists one AI decision record for live optimization output

### `create_campaign_copy`

- Demo mode: deterministic copy variants
- Live mode: uses the configured AI provider
- If the selected provider is not configured, returns `status=blocked`

### `analyze_audience_segments`

- Demo mode only in this repo
- Live mode returns `status=blocked` because no contact source is wired yet

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "marketing-automation": {
      "command": "python3",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/Marketing-Automation-MCP-Server"
    }
  }
}
```

## Testing

```bash
python3 -m compileall src tests dashboard
python3 -m pytest
```

The test suite covers:

- provider registry selection
- provider-backed AI engine flows
- deterministic demo mode behavior
- blocked live-mode behavior
- unified client metric aggregation
- CLI smoke paths

## Project Layout

```text
src/
  ai/
    providers/
  integrations/
  tools/
  ai_engine.py
  cli.py
  config.py
  database.py
  models.py
  server.py
dashboard/
tests/
```
