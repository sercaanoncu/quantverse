import pandas as pd

from scripts.populate_real_global_universe import (
    SOURCE_COLUMNS,
    _base_row,
    _bond_rows,
    _commodity_rows,
)


def test_population_rows_preserve_configured_as_of_date_and_schema():
    row = _base_row(
        ticker="AAA",
        name="Alpha",
        sleeve="global_equity_nasdaq",
        region="North America",
        country="United States",
        exchange="NASDAQ",
        currency="USD",
        source="unit",
        source_url="https://example.com",
        as_of_date="2026-06-30",
    )

    assert list(row) == SOURCE_COLUMNS
    assert row["as_of_date"] == "2026-06-30"
    assert row["source_method"] == "index_proxy"


def test_manual_review_proxy_rows_are_not_market_cap_rank_claims():
    frame = pd.DataFrame(_commodity_rows("2026-06-30") + _bond_rows("2026-06-30"))

    assert set(frame["source_method"]) == {"manual_review_required"}
    assert set(frame["asset_type"]) == {"proxy"}
    assert pd.to_numeric(frame["market_cap_usd"], errors="coerce").isna().all()
    assert frame["notes"].str.contains("proxy", case=False).all()
