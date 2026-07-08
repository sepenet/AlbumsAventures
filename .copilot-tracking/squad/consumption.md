---
description: "Squad consumption ledger: members, models, estimated tokens, cost, and AI credits"
---

# Squad Consumption Ledger

| Role | Member | Agent | Model | Tier | In Tokens | Cached | Out Tokens | Est. Cost (USD) | Est. Credits |
|---|---|---|---|---|---|---|---|---|---|
| researcher | Alpha | Task Researcher | — | fast | 60000 | 0 | 24000 | 0.4680 | 46.80 |
| lead | Beta | Task Planner | — | default | 60000 | 0 | 28000 | 0.6000 | 60.00 |
| developer | Gamma | Task Implementor | — | default | 553000 | 0 | 277000 | 5.814 | 581.40 |
| tester | Delta | Task Reviewer | — | fast | 399000 | 0 | 134000 | 2.6715 | 267.15 |
| architect | Epsilon | System Architecture Reviewer | — | default | 48000 | 0 | 18000 | 0.4140 | 41.40 |
| azure-architect | Zeta | Squad Azure Architect | — | default | 0 | 0 | 0 | 0.0000 | 0.00 |
| iac-author | Eta | Squad IaC Author | — | default | 0 | 0 | 0 | 0.0000 | 0.00 |
| deployer | Theta | Squad Deployer | — | default | 0 | 0 | 0 | 0.0000 | 0.00 |
| asbuilt-author | Iota | Squad As-Built Author | — | fast | 0 | 0 | 0 | 0.0000 | 0.00 |
| azure-diagnose | Kappa | Squad Azure Diagnose | — | fast | 0 | 0 | 0 | 0.0000 | 0.00 |
| security | Lambda | Security Planner | — | default | 48000 | 0 | 18000 | 0.4140 | 41.40 |
| rai | Mu | RAI Planner | — | default | 12000 | 0 | 4500 | 0.1035 | 10.35 |
| designer | Nu | UX UI Designer | — | default | 0 | 0 | 0 | 0.0000 | 0.00 |
| fact-checker | Xi | Finding Deep Verifier | — | fast | 0 | 0 | 0 | 0.0000 | 0.00 |
| cost-manager | Omicron | Squad Cost Manager | — | default | 48000 | 0 | 18000 | 0.4140 | 41.40 |
| modernizer | Pi | Squad Modernization Planner | — | default | 0 | 0 | 0 | 0.0000 | 0.00 |
| product-owner | Sigma | GitHub Backlog Manager | — | default | 48000 | 0 | 18000 | 0.4140 | 41.40 |
| scribe | Rho | Squad Scribe | — | fast | 0 | 0 | 0 | 0.0000 | 0.00 |
| **Total** | | | | | **1186000** | **0** | **511500** | **$10.406** | **1040.60** |

> **Basis**: Turns 1–17 cumulative. Includes research (T1), council (T2), Phase 1 implement/review (T3), Phase 2 implement/review (T4), Phase 3 plan (T6), Phase 3 increment 1 (T6), Phase 3 increment 3.3 (T7), Phase 3 increment 3.4 implement+review (T8), Phase 3 increment 3.5+FU-1 implement+review (T9), Phase 3 increment 3.6+F-1 fix implement+review (T10), Phase 3 increment 3.7 shared-album implement+review (T11), Phase 3 increment 3.8 auth+C-8+FU-group implement+review (T12), Phase 3 increment 3.9 CSP tighten implement+review (T13), Phase 4 PWA (vite-plugin-pwa) implement+review (T14) — MODERNIZATION FINAL, Turn 16 Jinja Decommission research + plan + council + implement (2 dispatches: main + D1 fix) + review — JINJA-DECOMMISSION PIPELINE COMPLETE THROUGH REVIEW, and **Turn 17 Jinja Decommission implement increment 2 (2 dispatches) + review increment 2 — JINJA-DECOMMISSION COMPLETION FULL**. Estimated, not billed. No per-dispatch token telemetry exists; the runtime exposes only the per-user aggregate `ai_credits_used` via the Copilot usage-metrics REST API (optional post-hoc reconciliation). Token rates from `consumption-rates.md` (default-tier rates assumed pending verification). 1 AI credit = $0.01 USD.

---

## Cost Comparison: Squad Run vs. Manual Single-Model Baseline

**Squad Run (T1–T17)**: $10.406 USD ≈ 1040.60 AI credits

**Manual single-model baseline**: Assume a single developer role (Claude Sonnet 4.6 / default tier) iterating through all 17 turns sequentially without parallel research/council/review:
- Estimated 17 iterations × ~1.5 turns per increment (research → plan → implement → review cycle) ≈ ~25.5 manual turns
- Per-turn estimated cost: (40000 input × $3.00 + 20000 output × $15.00) / 1e6 ≈ $0.42 USD per turn
- Estimated manual baseline: 25.5 × $0.42 ≈ **$10.71 USD**

**Savings**: ($10.71 - $10.406) / $10.71 ≈ **2.8% cost savings + parallel dispatch speed (9 roles running concurrently at peak)**

> **Disclaimer**: Estimated, not billed. Baseline is a rough model; actual manual costs would depend on iteration count, parallelization, and re-work cycles. This comparison supports run planning, not invoicing.

