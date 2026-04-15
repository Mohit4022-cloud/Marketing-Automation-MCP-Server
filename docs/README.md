# Documentation

This docs set is aligned to the repo as it exists today.

## Start Here

- [Quick Start](./quickstart.md)
- [API Reference](./api/README.md)
- [Example Workflows](./examples/README.md)
- [Operator Runbook](./operator-runbook.md)
- [System Audit Review Docs](./reviews/README.md)
- [Repo Demo Guide](../DEMO_README.md)

## Runtime Policy

- Supported Python: `3.12` and `3.13`
- Preferred bootstrap: `uv`
- Supported MCP transport: `stdio`
- Python `3.14.x` is not the supported baseline for this repo yet

## Execution Model

- Demo mode is deterministic and suitable for contract testing.
- Live mode is honest: if credentials or providers are missing, tools return `status="blocked"`.
- Audience segmentation is demo-only in the current repo shape.

## Documentation Intent

The docs here are intentionally narrower than the older marketing-oriented material:
- commands should be runnable
- payload examples should match current Pydantic models
- stale or aspirational interfaces should be called out explicitly instead of implied as working
