# Environment Compatibility Matrix

| Surface | Before | Current target | Notes |
|---|---|---|---|
| Local development | Python `3.14.3` on this machine | Python `3.13` via `uv`, with `3.12` also supported | `3.14.x` is not the supported baseline yet |
| `pyproject.toml` | `>=3.10` | `>=3.12,<3.14` | Matches supported policy |
| Docker | `python:3.10-slim` | `python:3.13-slim` | Uses `uv sync --frozen` |
| CI test matrix | `3.10`, `3.11`, `3.12` | `3.12`, `3.13` | Uses `uv` and import smoke checks |
| Bootstrap workflow | mixed `pip` and duplicated dependency files | `uv sync --python 3.13 --extra dev` | One canonical path |
| Dependency source of truth | `pyproject.toml` plus duplicated `requirements.txt` | `pyproject.toml` | `requirements.txt` now installs the local project |
| MCP transport | implied stdio | explicit stdio | HTTP not documented as supported |

## Validation Expectations

- `uv sync --python 3.13 --extra dev`
- `uv run python -m compileall src tests dashboard`
- `uv run pytest`
- `uv run python -c "import src.server, src.cli, src.ai_engine, src.performance; print('imports ok')"`
- `docker build -t marketing-automation-mcp:latest .`
