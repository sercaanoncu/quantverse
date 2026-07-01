# QuantVerse Doctoral Output Red-Team Review

Review date: 2026-07-02

## Review Result

Status: pass with unresolved blockers disclosed.

The thesis package is acceptable as a doctoral-style research artifact because
it treats blockers as findings instead of hiding them. It is not acceptable as
a claim that a global USD master portfolio has been promoted.

## Red-Team Checklist

| Question | Result | Evidence / correction |
|---|---|---|
| Does the thesis hide blockers? | Pass | Blockers are listed in Results, Limitations, Red-Team Review and Evidence Pack. |
| Does it overclaim exact top-100? | Pass | It states that exact top-100 market-cap support is not available without market-cap/rank evidence. |
| Does it overclaim global USD promotion? | Pass | Current decision is `insufficient_inputs` / not promoted. |
| Does it confuse current universe with point-in-time history? | Pass | Current universe is described as forward-looking/current research input only. |
| Does it present ML as allocation signal? | Pass | ML is diagnostic unless strict validation exists. |
| Does it present Black-Litterman as valid without priors? | Pass | Black-Litterman is blocked by missing market-cap priors. |
| Does it use raw table dumps instead of explanation? | Pass | Main thesis uses narrative summaries and evidence references; long tables remain in generated evidence files. |
| Does it mention limitations clearly? | Pass | Missing source CSVs, FX, market-cap/rank evidence, point-in-time constituents, delistings and corporate actions are explicit. |
| Does it include reproducibility commands? | Pass | Commands are included in the reproducibility chapter and appendices. |
| Does it distinguish local returns from USD returns? | Pass | FX chapter states the local-to-USD simple-return formula. |
| Does it cite internal methodology and web thesis standards? | Pass | `thesis_style_source_audit.md` and `methodology_literature_mapping.md` are referenced. |
| Does it avoid investment advice language? | Pass | Non-advice disclaimer appears in front matter and appendices. |

## Remaining Unresolved Risks

- Missing sourced global equity CSVs prevent a real global master portfolio
  promotion.
- Exact top-100 market-cap claims are unsupported until dated market-cap/rank
  evidence exists.
- Point-in-time historical validation is unavailable without dated constituents,
  delistings and corporate actions.
- Public data-provider limitations remain; institutional reconciliation is not
  implemented.
- Extreme model metrics must be treated as warning signs until data, FX and
  walk-forward validation mature.
