# Global Master Portfolio Runbook

Run the pipeline stages independently while inputs are being assembled:

```powershell
python scripts/build_current_global_universe.py --config configs/current_global_universe.yaml
python scripts/build_global_returns_matrix.py --config configs/global_returns_matrix.yaml
python scripts/run_global_master_portfolio.py --config configs/global_master_portfolio.yaml
python scripts/run_global_portfolio_projection.py --config configs/global_portfolio_projection.yaml
```

Or run the graceful orchestrator:

```powershell
python scripts/run_global_quant_research.py --config configs/global_quant_research.yaml
```

If sourced universe files or returns are missing, scripts exit with status 0 and
write an explicit status message. This prevents missing research inputs from
being mistaken for model evidence.

If the sourced global equity universe is missing, any proxy-only smoke output is
not a promoted global master portfolio.
