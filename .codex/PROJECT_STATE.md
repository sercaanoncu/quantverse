# Project State

Main branch is the source of truth after the global quant input gate guardrail.

Current expected validation target: `102 passed`.

The global quant pipeline exists, including current universe builder, returns
matrix builder, Black-Litterman, master allocator, random portfolio benchmark,
Equal Weight comparison, Monte Carlo, stress tests and projection outputs.

The sourced global equity universe is still missing. The next major work is
real sourced top-100 universe population with source URLs, as-of dates and
market-cap/rank coverage reporting.

Root context files now define durable repo rules: `AGENTS.md`,
`PROJECT_CONTEXT.md`, `PIPELINE_CONTEXT.md`, `TESTING.md` and `DEBUGGING.md`.
