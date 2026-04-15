# Remediation Roadmap

## Batch 1: Baseline Reproducibility

Status: completed in this pass

- standardize Python support to `3.12` and `3.13`
- adopt `uv` as the canonical bootstrap path
- align CI and Docker to the same runtime policy
- replace archived `aioredis`
- refresh operator-facing docs

## Batch 2: Contract Enforcement

Next recommended implementation batch:

- add a small docs-contract validation script that checks for known stale fields in docs
- add server-level tests that assert the four tool names remain stable
- add explicit smoke coverage for `FastMCP` imports and tool registration

## Batch 3: Persistence and Replay Safety

Next recommended implementation batch:

- audit all timestamp-based IDs in `src/database.py`
- decide where true append-only history is desired versus where idempotent upserts are better
- document which writes are audit history and which are cache-like internal state

## Batch 4: GTM-System Fit

Next recommended implementation batch:

- decide whether this repo stays a marketing automation demo server or becomes a GTM operating-system component
- remove, quarantine, or fully implement placeholder modules under `src/tools/`
- tighten output conventions around confidence, rationale, and review status for every externally consumed workflow

## Batch 5: Optional MCP Expansion

Only pursue if a concrete operator need exists:

- expose MCP resources for operator guidance or capability inspection
- expose prompts only if they improve deterministic operator workflows
- add `streamable-http` only if the deployment model requires a remotely hosted MCP service
