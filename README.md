# Marketing Automation MCP Server

`marketing-automation-mcp` is a Python MCP server for deterministic campaign reporting, provider-backed budget optimization, copy generation, and demo-only audience segmentation.

This repo now favors reproducibility over ad hoc setup:
- Supported Python: `3.12` and `3.13`
- Local bootstrap: `uv`
- Primary MCP transport: `stdio`
- Local Python `3.14.x` is treated as compatibility work, not the supported baseline

## Current Scope

The public MCP contract in this repo is intentionally narrow:
- `generate_campaign_report`
- `optimize_campaign_budget`
- `create_campaign_copy`
- `analyze_audience_segments`

Only these four tools are part of the supported server surface today. Other modules under `src/tools/` exist as internal or aspirational code paths and should not be treated as production MCP features.

## Execution Modes

- `DEMO_MODE=true`
  Returns deterministic sample data for demos and contract testing.
- `DEMO_MODE=false`
  Uses real platform credentials and the selected AI provider.
  Missing live dependencies return structured `blocked` responses instead of fabricated output.

## Clean Machine Setup

```bash
uv sync --python 3.13 --extra dev
cp .env.example .env
uv run python -m compileall src tests dashboard
uv run pytest
```

If you need a pip fallback:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run The Server

Start the MCP server in its supported transport mode:

```bash
uv run python -m src.server
```

The server currently documents and supports `stdio` transport only.

Claude Desktop configuration:

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

## Configure

```bash
cp .env.example .env
```

Minimum useful configurations:

- Demo mode only:
  - `DEMO_MODE=true`
- Live reporting and optimization:
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

For stable live behavior, set:

- `SECRET_KEY`
- `ENCRYPTION_KEY`

If `ENCRYPTION_KEY` is missing, API-key encryption is disabled for that process and the server logs a warning.

## Tool Contract

Every tool response includes these top-level fields:

```json
{
  "status": "ok | blocked",
  "mode": "demo | live",
  "blocked_reason": "optional string",
  "warnings": []
}
```

See the full contract in [docs/api/README.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/api/README.md).

## Internal Write Side Effects

Live report and optimization flows may persist internal audit records to the configured database:
- report flows can persist normalized campaign snapshots
- optimization flows can persist AI decision history

These writes are internal side effects for observability and replay safety. They are not part of the public MCP response contract.

## Validation Commands

```bash
uv run python -m compileall src tests dashboard
uv run pytest
uv run python -c "import src.server, src.cli, src.ai_engine, src.performance; print('imports ok')"
docker build -t marketing-automation-mcp:latest .
```

## Documentation

- [Quick start](./docs/quickstart.md)
- [API reference](./docs/api/README.md)
- [Example workflows](./docs/examples/README.md)
- [Demo guide](./DEMO_README.md)
- [Operator runbook](./docs/operator-runbook.md)
- [System audit review docs](./docs/reviews/README.md)
