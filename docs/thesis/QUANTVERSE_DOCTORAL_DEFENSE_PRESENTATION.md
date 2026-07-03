# QuantVerse Doctoral Defense Presentation

This source defines a 27-slide doctoral-style defense deck. Each slide has one
main message, one evidence source and one decision implication.

| Slide | Title | Main message | Evidence source | Decision implication |
|---:|---|---|---|---|
| 1 | QuantVerse Defense | QuantVerse is an evidence-gated global portfolio research system. | Thesis manuscript | This is research, not investment advice. |
| 2 | Research motivation | Quant models can mislead when data and validation blockers are hidden. | Master roadmap | Blockers must be visible before performance. |
| 3 | Problem statement | The system must distinguish candidate generation from promotable evidence. | Decision summary | A candidate is not automatically promoted. |
| 4 | Research questions | The thesis asks what evidence is required before global portfolio claims. | Thesis research questions | The defense evaluates evidence, not hype. |
| 5 | Contribution summary | Contributions are gates for FX, source evidence, exact/proxy, BL prerequisites and reporting. | Thesis contribution statement | Governance is the main contribution. |
| 6 | Why evidence-gated research | "Not promoted" can be the scientifically correct result. | Academic evidence pack | False positives are more dangerous than honest blockers. |
| 7 | System architecture | The architecture lets each layer block unsupported claims. | Thesis architecture diagram | Claims must pass layer-by-layer checks. |
| 8 | Data governance | Ticker rows require source, provider, as-of date and investability metadata. | Source population docs | Missing evidence blocks exact claims. |
| 9 | Universe construction | Current/proxy universes are not point-in-time historical universes. | Sourced universe docs | Historical top-100 claims remain blocked. |
| 10 | FX normalization | Local returns must be converted to USD before global USD promotion. | FX policy | Mixed currencies block global USD promotion. |
| 11 | Market-cap/rank evidence | Exact top-100 requires dated market-cap or rank evidence. | Market-cap evidence report | Proxy lists cannot be called exact top-100. |
| 12 | Exact top-100 vs proxy | The system separates exact, proxy and source-unavailable states. | Exact/proxy report | Exact top-100 claim is unsupported where evidence is missing. |
| 13 | Portfolio construction | Optimizer weights are candidates subject to constraints and gates. | Candidate weights and constraint audit | Weights are not a promotion decision. |
| 14 | Model governance | Models are labelled as run, blocked, diagnostic or future. | Model applicability matrix | Blocked models are not allocation evidence. |
| 15 | Risk diagnostics | Return must be interpreted with drawdown, CVaR, stress and volatility. | Risk outputs | Higher return alone is insufficient. |
| 16 | Statistical diagnostics | Normality, stationarity, covariance and PCA are diagnostics. | Scientific sanity audit | Diagnostics do not prove alpha. |
| 17 | Audit engine | The audit found red flags and promotion blockers. | Scientific sanity summary | Audit issues are explicit, not hidden. |
| 18 | Reporting engine | Reports must explain decisions before raw tables. | Visual report and Excel START_HERE | Non-specialists can locate blockers and weights. |
| 19 | Reproducibility | Commands, tests and generated-output rules make the package repeatable. | Validation docs | Results should be rebuildable locally. |
| 20 | Test and validation results | Baseline pytest passed 117 tests before thesis generation. | Sprint validation output | Code health is verified before reporting. |
| 21 | Main findings | Current global master decision is insufficient inputs. | Decision summary | Global USD master portfolio is not promoted. |
| 22 | Why not promoted | Source universe, exact top-100, BL priors and point-in-time evidence are incomplete. | Evidence pack | Non-promotion is the correct conclusion. |
| 23 | Limitations | Missing sourced CSVs, delistings, corporate actions and vendor reconciliation remain. | Thesis limitations | Future work is data-governance heavy. |
| 24 | Red-team review | The thesis was checked for overclaim and blocker hiding. | Red-team review | The package passes as research, not as promoted portfolio evidence. |
| 25 | Future work | Populate sourced equity CSVs, rebuild FX-normalized returns and run walk-forward gates. | Thesis future work | Next sprint must attack data blockers first. |
| 26 | Conclusion | QuantVerse is strongest as an honest evidence-gated research system. | Thesis conclusion | It should not claim investable superiority yet. |
| 27 | Q&A | The central defense is why the system refuses unsupported claims. | Thesis and evidence pack | Questions should focus on evidence and blockers. |
