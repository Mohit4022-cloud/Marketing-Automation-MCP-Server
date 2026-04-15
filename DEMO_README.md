# Demo Guide

This repo supports a deterministic demo mode. Use it to validate the MCP contract and show the workflow shape without requiring live provider or platform credentials.

## Recommended Demo Path

Use the verified CLI flow in demo mode:

```bash
cp .env.example .env
uv sync --python 3.13 --extra dev
export DEMO_MODE=true

uv run marketing-automation report --campaign-ids camp_001 --campaign-ids camp_002
uv run marketing-automation optimize --campaign-ids camp_001 --campaign-ids camp_002 --budget 5000
uv run marketing-automation copy --product "Marketing OS" --description "Turns campaign data into actions" --audience "Marketing leaders"
uv run marketing-automation segment
```

Expected demo behavior:
- `status="ok"`
- `mode="demo"`
- deterministic outputs for repeated inputs

## Demo Assets In This Repo

The repo still contains several presentation-oriented assets:

- [demo.py](/Users/mohit/Marketing-Automation-MCP-Server/demo.py)
- [quick_demo.py](/Users/mohit/Marketing-Automation-MCP-Server/quick_demo.py)
- [simple_dashboard.py](/Users/mohit/Marketing-Automation-MCP-Server/simple_dashboard.py)
- [dashboard/app.py](/Users/mohit/Marketing-Automation-MCP-Server/dashboard/app.py)

Treat these as illustrative demo assets, not as the supported MCP contract.

Important caveats:
- some scripts still use hardcoded sample business narratives
- they are not the source of truth for the public tool schema
- they are useful for presentation or exploration, but not for contract validation

## Running The MCP Server In Demo Mode

```bash
export DEMO_MODE=true
uv run python -m src.server
```

Use this when you want to connect an MCP client such as Claude Desktop to the deterministic server output.

## Optional Visual Demo Assets

If you want a browser-based artifact in addition to the CLI:

```bash
uv run python simple_dashboard.py
```

or:

```bash
uv run python quick_demo.py
```

These flows are useful for showing a concept quickly, but the authoritative behavior remains the MCP tools and their documented outputs.

## What Demo Mode Is Good For

- contract testing
- operator onboarding
- showing blocked vs non-blocked workflow shapes
- validating that docs and commands still work on a clean environment

## What Demo Mode Is Not

- live ad-platform execution
- proof of production platform connectivity
- proof that audience segmentation is wired to a real contact source
- proof of exact commercial lift claims

For the supported contract, use:
- [README.md](/Users/mohit/Marketing-Automation-MCP-Server/README.md)
- [docs/api/README.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/api/README.md)
- [docs/operator-runbook.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/operator-runbook.md)
