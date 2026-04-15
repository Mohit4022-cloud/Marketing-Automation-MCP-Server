# MCP Contract Drift Report

## Server Surface

### Resolved

- The server now uses `FastMCP(json_response=True)` instead of a manual low-level handler layer.
- The public tool names are preserved:
  - `generate_campaign_report`
  - `optimize_campaign_budget`
  - `create_campaign_copy`
  - `analyze_audience_segments`

### Explicit Decision

- Supported transport remains `stdio`.
- `Streamable HTTP` is not documented as a supported runtime for this repo yet.

## Docs vs Models

### Resolved drift

- Python version guidance updated from `3.8+` to the current supported policy.
- Copy examples now use `best_variant_id`, which matches `CreateCampaignCopyOutput`.
- Quickstart no longer claims the server prints startup banners that are not part of the current implementation.
- Example payloads now match the current Pydantic model fields.

### Remaining deliberate constraints

- `analyze_audience_segments` remains demo-only in this repo.
- Internal database writes for live report and optimize flows remain side effects, not response fields.

## Tool-by-Tool Checklist

### `generate_campaign_report`

- Schema matches current input model: yes
- Demo mode deterministic: yes
- Live blocked behavior explicit: yes
- Internal write side effect documented: yes

### `optimize_campaign_budget`

- Schema matches current input model: yes
- Demo mode deterministic: yes
- Live blocked behavior explicit: yes
- Rationale exposed per allocation: yes
- Confidence exposed at top level: yes

### `create_campaign_copy`

- Schema matches current input model: yes
- Demo mode deterministic: yes
- Live blocked behavior explicit: yes
- Best-variant identifier aligned to model: yes

### `analyze_audience_segments`

- Schema matches current input model: yes
- Demo mode deterministic: yes
- Live blocked behavior explicit: yes
- Live contact-source integration present: no

## Non-Contract Modules

The following modules are not part of the supported MCP tool contract and should not be represented as production-ready server surfaces without further work:
- `src/tools/analytics.py`
- `src/tools/campaigns.py`
- `src/tools/automation.py`
- `src/tools/contacts.py`
