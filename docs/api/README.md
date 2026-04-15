# Marketing Automation MCP API Reference

This document describes the current public tool contracts for the repo. It is intentionally narrower than the older docs: fields documented here exist in code today.

## Execution Contract

Every tool response includes:

```json
{
  "status": "ok | blocked",
  "mode": "demo | live",
  "blocked_reason": "optional string",
  "warnings": []
}
```

If a required dependency is missing in live mode, the tool returns `status="blocked"` instead of synthetic data.

## Tools

### `generate_campaign_report`

Input:

```json
{
  "campaign_ids": ["camp_001"],
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "metrics": ["impressions", "clicks", "conversions", "cost", "revenue", "roi"],
  "format": "json",
  "include_charts": true,
  "group_by": "campaign"
}
```

Output highlights:

```json
{
  "report_id": "uuid",
  "generated_at": "iso-datetime",
  "campaigns": [
    {
      "campaign_id": "camp_001",
      "campaign_name": "Campaign 001",
      "platform": "google_ads",
      "impressions": 10000,
      "clicks": 250,
      "conversions": 18,
      "cost": 500.0,
      "revenue": 1800.0,
      "ctr": 2.5,
      "conversion_rate": 7.2,
      "roi": 260.0
    }
  ],
  "summary": {
    "total_impressions": 10000,
    "total_clicks": 250,
    "total_conversions": 18,
    "total_cost": 500.0,
    "total_revenue": 1800.0,
    "average_ctr": 2.5,
    "average_conversion_rate": 7.2,
    "average_roi": 260.0
  }
}
```

### `optimize_campaign_budget`

Input:

```json
{
  "campaign_ids": ["camp_001", "camp_002"],
  "total_budget": 5000,
  "optimization_goal": "maximize_roi",
  "constraints": {
    "camp_001": { "min": 1000, "max": 3000 }
  },
  "historical_days": 30,
  "include_projections": true
}
```

Output highlights:

```json
{
  "optimization_id": "uuid",
  "optimization_goal": "maximize_roi",
  "allocations": [
    {
      "campaign_id": "camp_001",
      "campaign_name": "Campaign 001",
      "current_budget": 2500.0,
      "recommended_budget": 2900.0,
      "change_percentage": 16.0,
      "expected_impact": {
        "roi_change": 12.0,
        "conversion_change": 8.0,
        "cost_change": 15.0
      },
      "reasoning": "Best recent ROI trend"
    }
  ],
  "projected_improvement": {
    "roi_change": 12.0,
    "conversion_change": 8.0,
    "reach_change": 6.0,
    "cpa_change": -8.0
  },
  "confidence_score": 0.8,
  "recommendations": ["Increase budget 15%"]
}
```

### `create_campaign_copy`

Input:

```json
{
  "product_name": "Marketing OS",
  "product_description": "Turns campaign data into actions",
  "target_audience": "Marketing leaders",
  "tone": "professional",
  "copy_type": "ad_headline",
  "variants_count": 3,
  "keywords": ["automation", "roi"]
}
```

Output highlights:

```json
{
  "copy_generation_id": "uuid",
  "copy_type": "ad_headline",
  "best_variant_id": "uuid",
  "variants": [
    {
      "variant_id": "uuid",
      "content": "Unlock Marketing OS: Turns campaign data into actions.",
      "headline": "Unlock Marketing OS",
      "call_to_action": "Book a demo",
      "predicted_ctr": 3.1,
      "keywords": ["automation", "roi"]
    }
  ],
  "generation_metadata": {
    "provider": "openai",
    "model": "gpt-5.4"
  }
}
```

### `analyze_audience_segments`

Input:

```json
{
  "contact_list_id": "list_001",
  "criteria": ["demographics", "behavior"],
  "min_segment_size": 100,
  "max_segments": 5,
  "include_recommendations": true,
  "analyze_overlap": true
}
```

Output highlights:

```json
{
  "analysis_id": "uuid",
  "total_contacts": 2400,
  "segments": [
    {
      "segment_id": "uuid",
      "name": "High-Intent Buyers",
      "size": 320,
      "engagement_score": 0.55,
      "value_score": 0.62
    }
  ],
  "recommendations": [
    {
      "segment_name": "High-Intent Buyers",
      "strategy": "Use persona-specific proof points and a clear commercial wedge",
      "channels": ["email", "paid_social"],
      "timing": "Mid-week mornings",
      "rationale": "High value and engagement in the demo dataset"
    }
  ]
}
```

## Notes

- Audience segmentation is demo-only in the current repo shape.
- Live reporting and optimization require configured platform credentials.
- Live copy generation requires the selected AI provider to be configured.
- Live report and optimization flows may persist internal audit records to the configured database. Those writes are internal side effects, not part of the response contract.
