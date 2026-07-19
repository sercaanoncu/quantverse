"""Schema utilities for global security-selection universes.

The functions in this module are intentionally offline-only. They validate
user-supplied CSV universe files and do not fetch market data or infer current
top-100 rankings.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REQUIRED_UNIVERSE_COLUMNS = [
    "ticker",
    "name",
    "sleeve",
    "region",
    "country",
    "exchange",
    "currency",
    "asset_type",
    "sector",
    "industry",
    "market_cap_usd",
    "market_cap_rank",
    "as_of_date",
    "source",
    "data_provider",
    "investable",
    "benchmark_only",
    "signal_only",
    "include",
    "proxy_type",
    "notes",
]

ALLOWED_SLEEVES = {
    "global_equity_nasdaq",
    "global_equity_nyse",
    "global_equity_us",
    "global_equity_europe",
    "global_equity_germany",
    "global_equity_uk",
    "global_equity_turkey",
    "global_equity_china",
    "global_equity_china_hk",
    "global_equity_japan",
    "crypto_top100",
    "crypto",
    "commodity_real_assets",
    "defensive_bonds_cash",
    "etf_benchmark",
    "market_signal",
}

EQUITY_SLEEVES = {
    "global_equity_nasdaq",
    "global_equity_nyse",
    "global_equity_us",
    "global_equity_europe",
    "global_equity_germany",
    "global_equity_uk",
    "global_equity_turkey",
    "global_equity_china",
    "global_equity_china_hk",
    "global_equity_japan",
}

CRYPTO_SLEEVES = {"crypto", "crypto_top100"}

# Conservative stable-value taxonomy used as a portfolio eligibility gate. The
# list is intentionally broader than fiat-backed stablecoins because tokenized
# cash/fund products must not enter a risk-seeking crypto sleeve by accident.
STABLE_VALUE_CRYPTO_TOKENS = {
    "USDT",
    "USDC",
    "DAI",
    "BUSD",
    "TUSD",
    "USDP",
    "FDUSD",
    "PYUSD",
    "GUSD",
    "USDE",
    "USDS",
    "USD1",
    "USYC",
    "USDG",
    "USDY",
    "RLUSD",
    "USDF",
    "USDD",
    "BFUSD",
    "USDGO",
    "USDTB",
    "USD0",
    "U",
    "STABLE",
    "BUIDL",
}


def load_security_universe(path: str | Path) -> pd.DataFrame:
    """Load and validate a CSV security universe."""
    universe_path = Path(path)
    if not universe_path.exists():
        raise FileNotFoundError(f"Security universe file not found: {universe_path}")
    if universe_path.suffix.lower() != ".csv":
        raise ValueError(
            "Only CSV security universe files are supported in this sprint."
        )

    df = pd.read_csv(universe_path)
    validate_security_universe_schema(df)
    return df


def validate_security_universe_schema(df: pd.DataFrame) -> None:
    """Validate required columns and known sleeve labels."""
    missing = [column for column in REQUIRED_UNIVERSE_COLUMNS if column not in df]
    if missing:
        raise ValueError(
            "Security universe is missing required columns: " + ", ".join(missing)
        )

    invalid_sleeves = sorted(
        {
            str(value)
            for value in df["sleeve"].dropna().unique()
            if str(value) and str(value) not in ALLOWED_SLEEVES
        }
    )
    if invalid_sleeves:
        raise ValueError("Invalid sleeve values: " + ", ".join(invalid_sleeves))


def filter_included_investable_assets(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows that pass all portfolio-input eligibility gates."""
    validate_security_universe_schema(df)
    normalized = _with_boolean_flags(df)
    mask = (
        normalized["include_bool"]
        & normalized["investable_bool"]
        & ~normalized["benchmark_only_bool"]
        & ~normalized["signal_only_bool"]
    )
    mask &= ~stablecoin_like_mask(normalized)
    mask &= ~unverified_crypto_price_mapping_mask(normalized)
    return df.loc[mask].copy()


def split_universe_by_sleeve(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split a validated universe into sleeve-specific DataFrames."""
    validate_security_universe_schema(df)
    return {
        sleeve: sleeve_df.copy()
        for sleeve, sleeve_df in df.groupby("sleeve", dropna=False, sort=True)
    }


def summarize_security_universe(df: pd.DataFrame) -> pd.DataFrame:
    """Build a compact sleeve-level summary table."""
    validate_security_universe_schema(df)
    normalized = _with_boolean_flags(df)
    missing_caps = detect_missing_market_caps(df)
    stablecoins = detect_stablecoin_like_assets(df)
    unverified_crypto = detect_unverified_crypto_price_mappings(df)
    missing_by_sleeve = (
        missing_caps.groupby("sleeve").size().to_dict()
        if not missing_caps.empty
        else {}
    )
    stable_by_sleeve = (
        stablecoins.groupby("sleeve").size().to_dict() if not stablecoins.empty else {}
    )
    unverified_by_sleeve = (
        unverified_crypto.groupby("sleeve").size().to_dict()
        if not unverified_crypto.empty
        else {}
    )
    rows = []
    for sleeve, sleeve_df in normalized.groupby("sleeve", dropna=False, sort=True):
        rows.append(
            {
                "sleeve": sleeve,
                "rows": int(len(sleeve_df)),
                "included": int(sleeve_df["include_bool"].sum()),
                "investable": int(sleeve_df["investable_bool"].sum()),
                "benchmark_only": int(sleeve_df["benchmark_only_bool"].sum()),
                "signal_only": int(sleeve_df["signal_only_bool"].sum()),
                "missing_market_cap_rows": int(missing_by_sleeve.get(sleeve, 0)),
                "stablecoin_like_rows": int(stable_by_sleeve.get(sleeve, 0)),
                "unverified_crypto_price_mapping_rows": int(
                    unverified_by_sleeve.get(sleeve, 0)
                ),
            }
        )
    return pd.DataFrame(rows)


def detect_missing_market_caps(df: pd.DataFrame) -> pd.DataFrame:
    """Return included investable rows with missing or non-positive market caps."""
    validate_security_universe_schema(df)
    filtered = _with_boolean_flags(df)
    market_cap = pd.to_numeric(filtered["market_cap_usd"], errors="coerce")
    mask = (
        filtered["include_bool"]
        & filtered["investable_bool"]
        & filtered["sleeve"].isin(EQUITY_SLEEVES | {"crypto", "crypto_top100"})
        & (market_cap.isna() | (market_cap <= 0))
    )
    return df.loc[mask].copy()


def detect_survivorship_bias_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows that look like current constituents, not point-in-time history."""
    validate_security_universe_schema(df)
    normalized = _with_boolean_flags(df)
    source_text = (
        normalized["source"].fillna("").astype(str)
        + " "
        + normalized["notes"].fillna("").astype(str)
    ).str.lower()
    rank_missing = pd.to_numeric(normalized["market_cap_rank"], errors="coerce").isna()
    date_missing = normalized["as_of_date"].fillna("").astype(str).str.strip().eq("")
    template_or_current = source_text.str.contains(
        "template|current|today|latest|manual", regex=True
    )
    mask = (
        normalized["sleeve"].isin(EQUITY_SLEEVES)
        & normalized["include_bool"]
        & (template_or_current | date_missing | rank_missing)
    )
    issues = df.loc[mask, ["ticker", "sleeve", "source", "as_of_date", "notes"]].copy()
    if issues.empty:
        return pd.DataFrame(columns=["ticker", "sleeve", "issue", "severity"])
    issues["issue"] = (
        "Current or incomplete constituent metadata can create survivorship bias."
    )
    issues["severity"] = "warning"
    return issues[["ticker", "sleeve", "issue", "severity"]]


def detect_stablecoin_like_assets(df: pd.DataFrame) -> pd.DataFrame:
    """Flag stablecoin or stable-value crypto rows conservatively."""
    validate_security_universe_schema(df)
    mask = stablecoin_like_mask(df)
    return df.loc[mask].copy()


def detect_unverified_crypto_price_mappings(df: pd.DataFrame) -> pd.DataFrame:
    """Return crypto rows without an explicit, reviewed price-provider mapping."""
    validate_security_universe_schema(df)
    return df.loc[unverified_crypto_price_mapping_mask(df)].copy()


def is_stablecoin_like(ticker: object, name: object = "", notes: object = "") -> bool:
    """Classify stable-value crypto without treating the ``-USD`` quote as a signal."""
    base_symbol = re.sub(r"-USD$", "", str(ticker).strip().upper())
    name_text = str(name).strip().upper()
    notes_text = str(notes).strip().upper()
    if "STABLE_LIKE=TRUE" in notes_text:
        return True
    if base_symbol in STABLE_VALUE_CRYPTO_TOKENS:
        return True
    if base_symbol.startswith("USD") or base_symbol.endswith("USD"):
        return True
    return bool(
        re.search(
            r"\b(?:STABLECOIN|STABLE COIN|STABLES|USD|US DOLLAR|U\.S\. DOLLAR)\b",
            name_text,
        )
    )


def stablecoin_like_mask(df: pd.DataFrame) -> pd.Series:
    """Build a boolean stable-value mask aligned to ``df``."""
    sleeve = df.get("sleeve", pd.Series("", index=df.index)).astype(str)
    ticker = df.get("ticker", pd.Series("", index=df.index))
    name = df.get("name", pd.Series("", index=df.index))
    notes = df.get("notes", pd.Series("", index=df.index))
    classified = pd.Series(
        [
            is_stablecoin_like(ticker_value, name_value, notes_value)
            for ticker_value, name_value, notes_value in zip(ticker, name, notes)
        ],
        index=df.index,
        dtype=bool,
    )
    return sleeve.isin(CRYPTO_SLEEVES).astype(bool) & classified


def unverified_crypto_price_mapping_mask(df: pd.DataFrame) -> pd.Series:
    """Build a mask for crypto rows lacking explicit provider-symbol evidence."""
    sleeve = df.get("sleeve", pd.Series("", index=df.index)).astype(str)
    crypto = sleeve.isin(CRYPTO_SLEEVES).astype(bool)
    if "price_ticker_verified" not in df:
        verified = pd.Series(False, index=df.index, dtype=bool)
    else:
        verified = df["price_ticker_verified"].map(_to_bool).astype(bool)
    return crypto & ~verified


def validate_investable_vs_signal_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Return flag-combination issues without mutating the source frame."""
    validate_security_universe_schema(df)
    normalized = _with_boolean_flags(df)
    stablecoin_mask = stablecoin_like_mask(normalized)
    unverified_mapping_mask = unverified_crypto_price_mapping_mask(normalized)
    rows = []
    for idx, row in normalized.iterrows():
        issues = []
        if row["signal_only_bool"] and row["investable_bool"]:
            issues.append("signal_only rows should not be marked investable")
        if row["benchmark_only_bool"] and row["signal_only_bool"]:
            issues.append("row cannot be both benchmark_only and signal_only")
        if (
            row["benchmark_only_bool"]
            and row["include_bool"]
            and row["investable_bool"]
        ):
            issues.append("benchmark_only rows should not be selected as investable")
        if stablecoin_mask.loc[idx] and (row["investable_bool"] or row["include_bool"]):
            issues.append(
                "stablecoin/stable-value crypto rows cannot be investable portfolio inputs"
            )
        if unverified_mapping_mask.loc[idx] and row["investable_bool"]:
            issues.append(
                "crypto price-provider mapping must be explicitly verified before investment"
            )
        for issue in issues:
            rows.append(
                {
                    "row_index": int(idx),
                    "ticker": row["ticker"],
                    "issue": issue,
                    "severity": "error",
                }
            )
    return pd.DataFrame(rows, columns=["row_index", "ticker", "issue", "severity"])


def _with_boolean_flags(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in ["investable", "benchmark_only", "signal_only", "include"]:
        normalized[f"{column}_bool"] = normalized[column].map(_to_bool)
    return normalized


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
