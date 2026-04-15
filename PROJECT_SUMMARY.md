# Project Summary

## Current Repo Shape

`marketing-automation-mcp` is a Python MCP server with a narrow supported surface:

- `generate_campaign_report`
- `optimize_campaign_budget`
- `create_campaign_copy`
- `analyze_audience_segments`

It is designed around two explicit execution modes:

- `DEMO_MODE=true`
  deterministic sample outputs for demos and contract testing
- `DEMO_MODE=false`
  live mode that uses configured platform credentials and the selected AI provider, or returns structured `blocked` responses when prerequisites are missing

## Supported Runtime

- Python `3.12` and `3.13`
- `uv` for local bootstrap and dependency management
- `stdio` as the supported MCP transport

The repo now carries a `uv.lock` file and aligns local setup, CI, and Docker around the same dependency source of truth.

## Main Components

### MCP Server

- [src/server.py](/Users/mohit/Marketing-Automation-MCP-Server/src/server.py)
- `FastMCP(json_response=True)`
- preserves the existing public tool names

### Tool Contracts

- [src/models.py](/Users/mohit/Marketing-Automation-MCP-Server/src/models.py)
- [src/tools/marketing_tools.py](/Users/mohit/Marketing-Automation-MCP-Server/src/tools/marketing_tools.py)
- explicit `status`, `mode`, `blocked_reason`, and `warnings`

### AI Layer

- [src/ai_engine.py](/Users/mohit/Marketing-Automation-MCP-Server/src/ai_engine.py)
- provider adapters under [src/ai/providers](/Users/mohit/Marketing-Automation-MCP-Server/src/ai/providers)
- OpenAI, Anthropic, and Gemini support through a shared abstraction

### Integrations

- Google Ads
- Facebook Ads
- Google Analytics
- unified access through [src/integrations/unified_client.py](/Users/mohit/Marketing-Automation-MCP-Server/src/integrations/unified_client.py)

### Persistence and Auditability

- [src/database.py](/Users/mohit/Marketing-Automation-MCP-Server/src/database.py)
- internal write side effects for live report snapshots and optimization decision history
- replay-safety improvements for some live writes

### Logging and Monitoring

- [src/logger.py](/Users/mohit/Marketing-Automation-MCP-Server/src/logger.py)
- [src/performance.py](/Users/mohit/Marketing-Automation-MCP-Server/src/performance.py)
- structured logging and optional Redis-backed performance monitoring

## Current Validation State

The current supported validation path is:

```bash
uv sync --python 3.13 --extra dev
uv run python -m compileall src tests dashboard
uv run pytest
uv run python -c "import src.server, src.cli, src.ai_engine, src.performance; print('imports ok')"
```

At the time of the last docs refresh, the repo passed the Python `3.13` test suite locally.

## Important Scope Notes

- audience segmentation is demo-only in the current repo
- some modules under `src/tools/` are placeholder or aspirational and are not part of the supported MCP contract
- legacy demo and dashboard scripts exist, but they are not the source of truth for the public interface

## Where To Look Next

- [README.md](/Users/mohit/Marketing-Automation-MCP-Server/README.md)
- [docs/quickstart.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/quickstart.md)
- [docs/api/README.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/api/README.md)
- [docs/operator-runbook.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/operator-runbook.md)
- [docs/reviews/README.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/reviews/README.md)
