# Contributing

This repo is maintained as a deterministic, reviewable MCP service. Contributions should improve reproducibility, contract clarity, and operator trust before adding new surface area.

## Development Baseline

- Supported Python: `3.12` and `3.13`
- Preferred bootstrap: `uv`
- Supported MCP transport: `stdio`
- Public MCP contract: the four tools documented in [README.md](/Users/mohit/Marketing-Automation-MCP-Server/README.md) and [docs/api/README.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/api/README.md)

## Local Setup

```bash
git clone https://github.com/Mohit4022-cloud/Marketing-Automation-MCP-Server.git
cd Marketing-Automation-MCP-Server
uv sync --python 3.13 --extra dev
cp .env.example .env
```

If you are only working in demo mode, external credentials are optional.

## Validation Before Opening A PR

Run the same checks the repo expects locally:

```bash
uv run python -m compileall src tests dashboard
uv run pytest
uv run flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
uv run flake8 src tests --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
uv run python -c "import src.server, src.cli, src.ai_engine, src.performance; print('imports ok')"
```

## Pull Request Expectations

1. Keep changes grounded in the current contract and runtime policy.
2. If you change a tool schema, response field, or supported environment behavior, update:
   - [README.md](/Users/mohit/Marketing-Automation-MCP-Server/README.md)
   - [docs/api/README.md](/Users/mohit/Marketing-Automation-MCP-Server/docs/api/README.md)
   - any affected quickstart or operator docs
3. If you change the MCP surface, preserve existing tool names unless the change is additive or explicitly versioned.
4. If you change demo/live behavior, add or update tests for:
   - deterministic demo mode
   - live blocked mode
   - live success mode if applicable

## Documentation Rules

- Prefer executable docs over aspirational docs.
- Do not describe unsupported transports or stale setup flows as working.
- Mark legacy demo or presentation assets as illustrative if they are not part of the supported MCP contract.

## Coding Guidelines

- Prefer modular, testable changes.
- Keep deterministic logic separate from provider-backed logic.
- Make write side effects explicit.
- Favor idempotent or replay-safe behavior for internal persistence when possible.
- Do not silently broaden the supported public interface.

## Commit Messages

Use clear, specific, imperative messages. Examples:

```text
update docs for uv-based bootstrap
replace aioredis with redis asyncio
migrate mcp server to fastmcp
```

## Reporting Bugs

When reporting a bug, include:

- Python version
- whether you used `uv` or another bootstrap path
- whether `DEMO_MODE` was `true` or `false`
- the command you ran
- the observed output or traceback

Use the GitHub issue templates in `.github/ISSUE_TEMPLATE/`.
