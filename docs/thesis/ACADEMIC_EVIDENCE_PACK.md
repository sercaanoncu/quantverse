# QuantVerse Academic Evidence Pack

This pack controls what QuantVerse may claim in an academic defense and what it
must not claim until evidence blockers are resolved.

## Source-of-Truth Documents

| Source | Role |
|---|---|
| `docs/roadmap/QUANTVERSE_MASTER_PROJECT_PLAN.md` | Permanent roadmap, architecture and definition of done. |
| `.codex/CONTEXT.md` | Operating context and no-fabrication guardrails. |
| `.codex/VALIDATION.md` | Local validation command standard. |
| `.codex/DO_NOT_DO.md` | Explicit forbidden actions and overclaim rules. |
| `PROJECT_CONTEXT.md` | Project purpose and risk assumptions. |
| `PIPELINE_CONTEXT.md` | Pipeline stages and validation checkpoints. |
| `TESTING.md` | Test and validation expectations. |
| `docs/data/global_returns_fx_policy.md` | Local versus USD return policy and FX conversion formula. |
| `docs/data/sourced_top100_universe_population.md` | Sourced top-100 input requirements. |
| `docs/audit/market_cap_rank_source_engine_plan.md` | Market-cap/rank evidence gate. |
| `docs/research/global_master_portfolio.md` | Global master portfolio research context. |
| `docs/research/global_master_portfolio_runbook.md` | Runbook and insufficient-input behavior. |

## Generated Evidence Files

Generated evidence is not committed, but it is used by the thesis builders when
present locally:

- `data/processed/global_master_decision_summary.json`
- `data/processed/global_scientific_sanity_summary.csv`
- `data/processed/global_scientific_sanity_issues.csv`
- `data/processed/global_red_flag_dashboard.csv`
- `data/processed/global_fx_normalization_report.csv`
- `data/processed/global_fx_rate_coverage_report.csv`
- `data/processed/global_market_cap_rank_evidence_report.csv`
- `data/processed/global_exact_proxy_classification_report.csv`
- `data/processed/global_market_cap_rank_blockers.csv`
- `data/processed/global_black_litterman_prerequisite_report.csv`
- `data/processed/global_master_model_comparison.csv`
- `data/processed/global_master_candidate_weights.csv`

## Claim Control Table

| Claim | Allowed? | Evidence | Blocker | Required Fix |
|---|---|---|---|---|
| QuantVerse is research-grade. | Yes, with limits. | Tests, docs, audit gates and reproducible scripts. | Not equivalent to production trading. | Keep validation and blocker language current. |
| QuantVerse is audit-ready. | Partially. | Scientific sanity outputs, evidence pack, red-team review. | Vendor-grade data lineage and access controls are absent. | Add institutional data controls and audit trail. |
| Real stocks entered analysis. | Yes, if described as current/proxy research input. | Universe and candidate weights outputs. | Point-in-time membership and some source evidence remain incomplete. | Add sourced dated equity universe files. |
| Global USD returns are FX-normalized. | Partially. | FX normalization reports and policy. | Current global master promotion still blocked/insufficient when source universe is missing. | Populate sourced universe and ensure all selected non-USD assets are FX-normalized. |
| Exact top-100 equities are supported. | No. | Market-cap/rank evidence report and blockers. | Missing market-cap/rank evidence for required sleeves. | Add sourced market-cap/rank fields with provider, URL and as-of date. |
| Black-Litterman is valid allocation evidence. | No. | Black-Litterman prerequisite report. | Sourced market-cap priors are missing. | Add market-cap priors and documented views, then validate. |
| Global USD master portfolio is promoted. | No. | `global_master_decision_summary.json`. | Insufficient sourced global equity universe and evidence blockers. | Populate source CSVs, rebuild returns, pass FX/market-cap/promotion gates. |
| Point-in-time historical claims are valid. | No. | Source population docs. | Current constituents are not point-in-time history. | Add dated historical constituents, delistings and corporate actions. |
| Project gives investment advice. | No. | README and thesis disclaimer. | The system is a research pipeline. | Keep non-advice language in user-facing outputs. |
| Project guarantees outperformance. | No. | Model governance and limitations. | No guarantee exists in financial markets. | Never use guarantee language. |

## Defense-Ready Status

The project is ready for a doctoral-style research-methodology defense when it:

1. states the research question clearly,
2. distinguishes data evidence from missing evidence,
3. shows current results without hiding blockers,
4. separates diagnostic models from allocation evidence,
5. records reproducibility commands,
6. passes tests and formatting checks.

It is not yet ready to defend a promoted global USD master portfolio.

## Promotable Global USD Master Portfolio Requirements

Promotion requires all of the following:

1. sourced global equity CSVs for all required sleeves,
2. market-cap/rank evidence for exact top-100 claims,
3. point-in-time membership for historical claims,
4. FX-normalized USD returns for all selected non-USD assets,
5. valid adjusted-price/corporate-action handling,
6. long-only/cap/weight constraints passing,
7. random portfolio and Equal Weight comparisons,
8. drawdown, VaR/CVaR, stress and transaction-cost checks,
9. chronological walk-forward evidence,
10. promotion gate result for the named universe.
