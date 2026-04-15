# Prioritized Findings

## P0

### Packaging and runtime policy were inconsistent

Before this pass:
- local runtime was `3.14.3`
- `pyproject.toml` allowed `>=3.10`
- Docker pinned `3.10`
- CI tested `3.10` to `3.12`

Impact:
- no single supported runtime baseline
- local failures were ambiguous
- reproducibility was weak

Remediation in this pass:
- standardized supported Python to `3.12` and `3.13`
- added `.python-version`
- moved CI and Docker to the same policy
- adopted `uv` as the canonical bootstrap path

### Public docs were not trustworthy

Before this pass:
- docs still claimed Python `3.8+`
- quickstart referenced startup output that the current server does not emit
- examples referenced fields like `best_performer_index` that do not exist in current models

Impact:
- operator onboarding was misleading
- docs could not be used as executable validation

Remediation in this pass:
- rewrote `README.md`
- rewrote `docs/README.md`, `docs/quickstart.md`, and `docs/examples/README.md`
- added an operator runbook

## P1

### The server surface lagged behind current MCP Python SDK ergonomics

Before this pass:
- the repo used low-level `Server` handlers
- JSON serialization was manual
- the tool surface was harder to inspect and maintain

Impact:
- unnecessary glue code
- higher contract-maintenance burden

Remediation in this pass:
- migrated to `FastMCP(json_response=True)`
- preserved the four public tool names
- kept `stdio` as the documented transport

### Archived Redis dependency remained in the tree

Before this pass:
- `aioredis` was declared and used in `src/performance.py`
- upstream is archived and directs users to `redis.asyncio`

Impact:
- dependency risk
- avoidable upgrade friction

Remediation in this pass:
- replaced `aioredis` with `redis.asyncio`

### Internal writes were not replay-safe enough

Before this pass:
- live report snapshots used timestamp-based `metric_id` values
- optimization decision history used timestamp-based IDs only

Impact:
- repeated runs could create noisy duplicate audit rows

Remediation in this pass:
- made report snapshot IDs stable by campaign and report window
- made optimization decision IDs stable from allocation content in the live path

## P2

### Secret handling favored convenience over explicitness

Before this pass:
- API-key encryption silently generated a temporary encryption key
- session-token helpers in `src/security.py` accepted a hard-coded default secret

Impact:
- non-replayable encryption behavior
- insecure token behavior if operators missed configuration

Remediation in this pass:
- disabled API-key encryption when `ENCRYPTION_KEY` is absent and logged a clear warning
- required `SECRET_KEY` for session-token helpers

### The repo still contains aspirational modules outside the supported MCP surface

Examples:
- `src/tools/analytics.py`
- `src/tools/campaigns.py`
- `src/tools/automation.py`
- `src/tools/contacts.py`

Impact:
- repo shape can suggest broader production capability than the supported MCP contract actually provides

Current status:
- documented these as non-contract surfaces
- deferred deeper consolidation to the roadmap
