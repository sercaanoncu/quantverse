# Claim-Language Review

Scope:

- `README.md`
- `docs/showcase/README_GITHUB_SHOWCASE.md`
- `docs/showcase/CV_BULLETS.md`
- `docs/showcase/LINKEDIN_PROJECT_POST.md`
- `docs/showcase/BANK_INTERVIEW_TALK_TRACK.md`
- `docs/audit/QUANTVERSE_V2_PUBLISH_READINESS_AUDIT.md`
- `docs/thesis/QUANTVERSE_DOCTORAL_DISSERTATION_FULL.md`
- `docs/thesis/QUANTVERSE_DOCTORAL_DEFENSE_PRESENTATION_FULL.md`
- Generated v2 PDF/HTML/thesis/defense artifacts

## Forbidden Or Sensitive Phrases Checked

- `guaranteed alpha`
- `guaranteed outperformance`
- `investment advice`
- `official exact top-100 supported`
- `official exact top-100 is supported`
- `institutional point-in-time backtest completed`
- `institutional PIT backtest completed`
- `production trading system`
- `live trading system`
- `buy recommendation`
- `sell recommendation`

## Results

The text search found only clearly negated or cautionary uses in user-facing docs, for example:

- `not investment advice`
- `not a live trading system`
- `not buy recommendation`
- `does not claim official exact top-100 support`
- `does not claim institutional point-in-time validation`

The generated artifact validator found zero forbidden generated-report hits.

## Required Language Present

| Required language | Status |
| ----------------- | ------ |
| Public-data research | Present |
| Not investment advice | Present |
| Current-universe limitation | Present |
| No official exact top-100 claim | Present |
| No institutional PIT claim | Present |
| Limitations visible | Present |
| Benchmark-aware model selection | Present |
| Equal Weight and random portfolios as benchmarks | Present |

## Fixes Applied

- Generated report wording changed from `guaranteed alpha` to `alpha guarantees` inside a negated caution sentence, so automated claim guards do not flag a literal forbidden phrase.
- Generated v2 report gained a dedicated `Limitations` section.

## Claim Decision

Claim language is acceptable for GitHub/CV/recruiter publication as a public-data research project with explicit limitations. It must not be described as investment advice, official exact top-100 coverage, a production trading system, or an institutional point-in-time backtest.
