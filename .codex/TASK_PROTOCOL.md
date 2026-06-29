# Task Protocol

Every future sprint should:

1. Inspect branch, status and recent commits first.
2. Read `AGENTS.md`, then the exact source, config, test and docs files relevant
   to the request.
3. Make the smallest coherent change that solves the problem.
4. Preserve the existing ETF/full pipeline unless explicitly asked to change it.
5. Keep optional dependencies optional.
6. Add deterministic tests that do not require live market data.
7. Run validation before reporting completion.
8. Exclude generated outputs from commits.
9. Use a structured final response with branch, files, behavior, tests, status,
   commit hash, limitations and next command.
