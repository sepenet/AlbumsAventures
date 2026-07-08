---
description: "Maintainable per-model token-rate table and comparison methodology for squad consumption estimates"
---

# Consumption Rates

Verify against the current GitHub Copilot "Models and pricing" docs at https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing

* Billing model: usage-based billing (UBB), token-metered, effective 2026-06-01.
* Observed-on: <verify>. Source: https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing
* Credit conversion: 1 AI credit = $0.01 USD (fixed).

## Per-model token rates in USD per 1M tokens (volatile, verify before commit)

| Model (as routed) | Tier | Input | Cached | Output | Notes |
|---|---|---|---|---|---|
| GPT-5.4 nano | fast | <verify> | <verify> | <verify> | lightweight, read-heavy |
| Claude Haiku 4.5 | fast | <verify> | <verify> | <verify> | lightweight reasoning |
| Claude Sonnet 4.6 | default | <verify> | <verify> | <verify> | versatile |
| Claude Opus 4.8 | default | <verify> | <verify> | <verify> | high-capability reasoning |

## Comparison methodology (token terms)

```
est_cost_usd = (input_tokens × input_rate + cached_tokens × cached_rate + output_tokens × output_rate) / 1e6
est_credits = est_cost_usd / 0.01
squad_cost = sum over dispatched roles of est_cost_usd
manual_baseline = expected_iterations × baseline_model_cost_per_turn
savings_pct = 1 - (squad_cost / manual_baseline)
```

All values are labeled estimated, and token counts are estimated because no per-dispatch telemetry exists. Optionally reconcile the run total against the per-user aggregate `ai_credits_used` from the usage-metrics REST API after the run.
