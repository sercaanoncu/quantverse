"""Populate sourced current global security universe candidate CSVs.

The script uses accessible public index/proxy sources. It does not claim that
index proxies are exact top-100-by-market-cap universes, and it leaves missing
market caps/ranks blank so downstream validation can report the gap honestly.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.data_pipeline.security_universe import is_stablecoin_like

SOURCE_COLUMNS = [
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
    "source_url",
    "data_provider",
    "investable",
    "benchmark_only",
    "signal_only",
    "include",
    "proxy_type",
    "source_method",
    "source_asset_id",
    "price_provider",
    "price_ticker",
    "price_ticker_verified",
    "price_mapping_method",
    "notes",
]

COMMODITY_PROXIES = [
    ("GLD", "SPDR Gold Shares", "gold", "https://finance.yahoo.com/quote/GLD/"),
    ("SLV", "iShares Silver Trust", "silver", "https://finance.yahoo.com/quote/SLV/"),
    (
        "CPER",
        "United States Copper Index Fund",
        "copper",
        "https://finance.yahoo.com/quote/CPER/",
    ),
    (
        "PPLT",
        "abrdn Physical Platinum Shares ETF",
        "platinum",
        "https://finance.yahoo.com/quote/PPLT/",
    ),
    (
        "PALL",
        "abrdn Physical Palladium Shares ETF",
        "palladium",
        "https://finance.yahoo.com/quote/PALL/",
    ),
    (
        "USO",
        "United States Oil Fund",
        "WTI crude oil",
        "https://finance.yahoo.com/quote/USO/",
    ),
    (
        "BNO",
        "United States Brent Oil Fund",
        "Brent crude oil",
        "https://finance.yahoo.com/quote/BNO/",
    ),
    (
        "UNG",
        "United States Natural Gas Fund",
        "natural gas",
        "https://finance.yahoo.com/quote/UNG/",
    ),
]

BOND_PROXIES = [
    (
        "SHY",
        "iShares 1-3 Year Treasury Bond ETF",
        "short treasury",
        "https://finance.yahoo.com/quote/SHY/",
    ),
    (
        "IEF",
        "iShares 7-10 Year Treasury Bond ETF",
        "intermediate treasury",
        "https://finance.yahoo.com/quote/IEF/",
    ),
    (
        "TLT",
        "iShares 20+ Year Treasury Bond ETF",
        "long treasury",
        "https://finance.yahoo.com/quote/TLT/",
    ),
    (
        "AGG",
        "iShares Core U.S. Aggregate Bond ETF",
        "aggregate bond",
        "https://finance.yahoo.com/quote/AGG/",
    ),
    (
        "TIP",
        "iShares TIPS Bond ETF",
        "inflation-linked treasury",
        "https://finance.yahoo.com/quote/TIP/",
    ),
    (
        "BIL",
        "SPDR Bloomberg 1-3 Month T-Bill ETF",
        "treasury bill/cash",
        "https://finance.yahoo.com/quote/BIL/",
    ),
    (
        "SGOV",
        "iShares 0-3 Month Treasury Bond ETF",
        "treasury bill/cash",
        "https://finance.yahoo.com/quote/SGOV/",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/populate_real_global_universe.yaml",
        help="Path to real global universe population YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    source_dir = Path(config.get("source_dir", "data/universe/sources"))
    output_dir = Path(config.get("output_dir", "data/processed"))
    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    as_of = str(config.get("as_of_date") or date.today().isoformat())
    session = requests.Session()
    session.headers.update({"User-Agent": str(config.get("user_agent", "Mozilla/5.0"))})
    limit = int(config.get("max_rows_per_sleeve", 100))
    timeout = int(config.get("request_timeout", 30))

    rows_by_file: dict[str, list[dict[str, Any]]] = {}
    issues: list[dict[str, Any]] = []

    specs = config.get("sources", {}) or {}
    _add(
        rows_by_file,
        "nasdaq_top100_candidates.csv",
        _nasdaq(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "nyse_top100_candidates.csv",
        _sp100(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "europe_top100_candidates.csv",
        _euro_stoxx(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "germany_top100_candidates.csv",
        _dax(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "uk_top100_candidates.csv",
        _ftse(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "turkey_top100_candidates.csv",
        _bist100(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "japan_top100_candidates.csv",
        _nikkei(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "china_hk_top100_candidates.csv",
        _hang_seng(session, specs, as_of, limit, timeout, issues),
    )
    _add(
        rows_by_file,
        "crypto_top100_candidates.csv",
        _coingecko(session, specs, as_of, limit, timeout, issues),
    )
    _add(rows_by_file, "commodity_candidates.csv", _commodity_rows(as_of))
    _add(rows_by_file, "bond_bill_candidates.csv", _bond_rows(as_of))

    _write_source_files(source_dir, rows_by_file)
    _write_compatibility_files(source_dir, rows_by_file)
    _write_reports(output_dir, rows_by_file, issues)
    total_rows = sum(len(rows) for rows in rows_by_file.values())
    print(f"Real global universe source rows written: {total_rows}")
    if issues:
        print(f"Population issues: {len(issues)}")
    return 0


def _add(
    target: dict[str, list[dict[str, Any]]], filename: str, rows: list[dict[str, Any]]
) -> None:
    target[filename] = rows


def _html_tables(
    session: requests.Session, url: str, timeout: int
) -> list[pd.DataFrame]:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return pd.read_html(StringIO(response.text))


def _issue(
    issues: list[dict[str, Any]], sleeve: str, source_url: str, issue: str, detail: str
) -> None:
    issues.append(
        {
            "sleeve": sleeve,
            "source_url": source_url,
            "issue": issue,
            "detail": detail[:500],
            "severity": "error" if issue.endswith("failed") else "warning",
        }
    )


def _pick_table(tables: list[pd.DataFrame], required: set[str]) -> pd.DataFrame:
    for table in tables:
        columns = {
            str(column).split("'")[-2] if isinstance(column, tuple) else str(column)
            for column in table.columns
        }
        if required.issubset(columns):
            table = table.copy()
            table.columns = [
                column[-1] if isinstance(column, tuple) else str(column)
                for column in table.columns
            ]
            return table
    raise ValueError(f"No table contains columns: {sorted(required)}")


def _base_row(
    *,
    ticker: str,
    name: str,
    sleeve: str,
    region: str,
    country: str,
    exchange: str,
    currency: str,
    source: str,
    source_url: str,
    asset_type: str | None = None,
    sector: str = "",
    industry: str = "",
    market_cap_usd: Any = "",
    market_cap_rank: Any = "",
    investable: bool = True,
    benchmark_only: bool = False,
    signal_only: bool = False,
    include: bool = True,
    proxy_type: str = "direct_listing",
    source_method: str = "index_proxy",
    data_provider: str = "public_web_source",
    source_asset_id: str = "",
    price_provider: str = "",
    price_ticker: str = "",
    price_ticker_verified: bool | str = "",
    price_mapping_method: str = "",
    as_of_date: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    row = {
        "ticker": ticker,
        "name": name,
        "sleeve": sleeve,
        "region": region,
        "country": country,
        "exchange": exchange,
        "currency": currency,
        "asset_type": asset_type
        or ("equity" if sleeve.startswith("global_equity") else "proxy"),
        "sector": sector,
        "industry": industry,
        "market_cap_usd": market_cap_usd,
        "market_cap_rank": market_cap_rank,
        "as_of_date": as_of_date or date.today().isoformat(),
        "source": source,
        "source_url": source_url,
        "data_provider": data_provider,
        "investable": bool(investable),
        "benchmark_only": bool(benchmark_only),
        "signal_only": bool(signal_only),
        "include": bool(include),
        "proxy_type": proxy_type,
        "source_method": source_method,
        "source_asset_id": source_asset_id,
        "price_provider": price_provider,
        "price_ticker": price_ticker,
        "price_ticker_verified": price_ticker_verified,
        "price_mapping_method": price_mapping_method,
        "notes": notes,
    }
    return {column: row.get(column, "") for column in SOURCE_COLUMNS}


def _nasdaq(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("nasdaq", {}).get(
        "url", "https://en.wikipedia.org/wiki/Nasdaq-100"
    )
    try:
        table = _pick_table(
            _html_tables(session, source_url, timeout), {"Ticker", "Company"}
        )
        rows = []
        for _, item in table.head(limit).iterrows():
            rows.append(
                _base_row(
                    ticker=_us_symbol(item["Ticker"]),
                    name=str(item["Company"]),
                    sleeve="global_equity_nasdaq",
                    region="North America",
                    country="United States",
                    exchange="NASDAQ",
                    currency="USD",
                    sector=str(item.get("ICB Industry[15]", "")),
                    industry=str(item.get("ICB Subsector[15]", "")),
                    source="Wikipedia Nasdaq-100 constituents",
                    source_url=source_url,
                    as_of_date=as_of,
                    notes=f"Nasdaq-100 index proxy retrieved {as_of}; not an exchange-wide top-100 market-cap ranking.",
                )
            )
        return rows
    except Exception as exc:
        _issue(
            issues, "global_equity_nasdaq", source_url, "source_fetch_failed", str(exc)
        )
        return []


def _sp100(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("nyse", {}).get(
        "url", "https://en.wikipedia.org/wiki/S%26P_100"
    )
    try:
        table = _pick_table(
            _html_tables(session, source_url, timeout), {"Symbol", "Name"}
        )
        return [
            _base_row(
                ticker=_us_symbol(item["Symbol"]),
                name=str(item["Name"]),
                sleeve="global_equity_nyse",
                region="North America",
                country="United States",
                exchange="NYSE/NASDAQ mixed large-cap proxy",
                currency="USD",
                sector=str(item.get("Sector", "")),
                source="Wikipedia S&P 100 constituents",
                source_url=source_url,
                as_of_date=as_of,
                notes=f"S&P 100 large-cap proxy retrieved {as_of}; not a pure NYSE top-100 market-cap ranking.",
            )
            for _, item in table.head(limit).iterrows()
        ]
    except Exception as exc:
        _issue(
            issues, "global_equity_nyse", source_url, "source_fetch_failed", str(exc)
        )
        return []


def _euro_stoxx(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("europe", {}).get(
        "url", "https://en.wikipedia.org/wiki/EURO_STOXX_50"
    )
    try:
        table = _pick_table(
            _html_tables(session, source_url, timeout), {"Ticker", "Name"}
        )
        return [
            _base_row(
                ticker=str(item["Ticker"]).strip(),
                name=str(item["Name"]),
                sleeve="global_equity_europe",
                region="Europe",
                country=str(item.get("Registered office", "Europe")),
                exchange=str(item.get("Main listing", "EURO STOXX 50 proxy")),
                currency="EUR",
                sector=str(item.get("Sector", "")),
                source="Wikipedia EURO STOXX 50 constituents",
                source_url=source_url,
                as_of_date=as_of,
                notes=f"EURO STOXX 50 index proxy retrieved {as_of}; not Europe top-100 by market cap.",
            )
            for _, item in table.head(limit).iterrows()
        ]
    except Exception as exc:
        _issue(
            issues, "global_equity_europe", source_url, "source_fetch_failed", str(exc)
        )
        return []


def _dax(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("germany", {}).get(
        "url", "https://en.wikipedia.org/wiki/DAX"
    )
    try:
        table = _pick_table(
            _html_tables(session, source_url, timeout), {"Ticker", "Company"}
        )
        return [
            _base_row(
                ticker=str(item["Ticker"]).strip(),
                name=str(item["Company"]),
                sleeve="global_equity_germany",
                region="Europe",
                country="Germany",
                exchange="DAX proxy",
                currency="EUR",
                sector=str(item.get("Prime Standard Sector", "")),
                source="Wikipedia DAX constituents",
                source_url=source_url,
                as_of_date=as_of,
                notes=f"DAX index proxy retrieved {as_of}; not Germany top-100 by market cap.",
            )
            for _, item in table.head(limit).iterrows()
        ]
    except Exception as exc:
        _issue(
            issues, "global_equity_germany", source_url, "source_fetch_failed", str(exc)
        )
        return []


def _ftse(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("uk", {}).get(
        "url", "https://en.wikipedia.org/wiki/FTSE_100_Index"
    )
    try:
        table = _pick_table(
            _html_tables(session, source_url, timeout), {"Company", "Ticker"}
        )
        return [
            _base_row(
                ticker=_suffix(str(item["Ticker"]), ".L"),
                name=str(item["Company"]),
                sleeve="global_equity_uk",
                region="Europe",
                country="United Kingdom",
                exchange="London Stock Exchange",
                currency="GBP",
                sector=str(
                    item.get("FTSE industry classification benchmark sector[39]", "")
                ),
                source="Wikipedia FTSE 100 constituents",
                source_url=source_url,
                as_of_date=as_of,
                notes=f"FTSE 100 index proxy retrieved {as_of}; Yahoo suffix .L applied for price lookup.",
            )
            for _, item in table.head(limit).iterrows()
        ]
    except Exception as exc:
        _issue(issues, "global_equity_uk", source_url, "source_fetch_failed", str(exc))
        return []


def _bist100(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("turkey", {}).get(
        "url", "https://www.kap.org.tr/en/Endeksler"
    )
    try:
        text = session.get(source_url, timeout=timeout).text
        start = text.find('\\"code\\":\\"XU100\\"')
        end = text.find('\\"indicesNo\\":100', start)
        if start < 0 or end < 0:
            raise ValueError("Could not locate embedded XU100 constituent payload.")
        pairs = re.findall(
            r'\\"stockCode\\":\\"([^\\"]+)\\",\\"title\\":\\"([^\\"]+)', text[start:end]
        )
        return [
            _base_row(
                ticker=f"{code}.IS",
                name=title,
                sleeve="global_equity_turkey",
                region="Europe / Middle East",
                country="Turkey",
                exchange="Borsa Istanbul",
                currency="TRY",
                source="KAP BIST 100 index constituents",
                source_url=source_url,
                as_of_date=as_of,
                notes=f"BIST 100 constituent proxy retrieved {as_of}; Yahoo suffix .IS applied for price lookup.",
            )
            for code, title in pairs[:limit]
        ]
    except Exception as exc:
        _issue(
            issues, "global_equity_turkey", source_url, "source_fetch_failed", str(exc)
        )
        return []


def _nikkei(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("japan", {}).get(
        "url",
        "https://topforeignstocks.com/indices/the-components-of-the-nikkei-225-index/",
    )
    try:
        table = _pick_table(
            _html_tables(session, source_url, timeout), {"Company Name", "Code"}
        )
        return [
            _base_row(
                ticker=str(item["Code"]).strip(),
                name=str(item["Company Name"]),
                sleeve="global_equity_japan",
                region="Asia",
                country="Japan",
                exchange="Tokyo Stock Exchange",
                currency="JPY",
                sector=str(item.get("Sector", "")),
                source="TopForeignStocks Nikkei 225 components",
                source_url=source_url,
                as_of_date=as_of,
                notes=f"Nikkei 225 component proxy retrieved {as_of}; verify current constituents before publication.",
            )
            for _, item in table.head(limit).iterrows()
        ]
    except Exception as exc:
        _issue(
            issues, "global_equity_japan", source_url, "source_fetch_failed", str(exc)
        )
        return []


def _hang_seng(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("china_hk", {}).get(
        "url", "https://en.wikipedia.org/wiki/Hang_Seng_Index"
    )
    try:
        table = _pick_table(
            _html_tables(session, source_url, timeout), {"Ticker", "Name"}
        )
        rows = []
        for _, item in table.head(limit).iterrows():
            ticker = _hk_symbol(str(item["Ticker"]))
            rows.append(
                _base_row(
                    ticker=ticker,
                    name=str(item["Name"]),
                    sleeve="global_equity_china_hk",
                    region="Asia",
                    country="Hong Kong / China",
                    exchange="Hong Kong Stock Exchange",
                    currency="HKD",
                    sector=str(item.get("Sub-index", "")),
                    source="Wikipedia Hang Seng Index constituents",
                    source_url=source_url,
                    as_of_date=as_of,
                    notes=f"Hang Seng Index proxy retrieved {as_of}; not China/HK top-100 by market cap.",
                )
            )
        return rows
    except Exception as exc:
        _issue(
            issues,
            "global_equity_china_hk",
            source_url,
            "source_fetch_failed",
            str(exc),
        )
        return []


def _coingecko(
    session: requests.Session,
    specs: dict,
    as_of: str,
    limit: int,
    timeout: int,
    issues: list,
) -> list[dict[str, Any]]:
    source_url = specs.get("crypto", {}).get(
        "url", "https://api.coingecko.com/api/v3/coins/markets"
    )
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": min(limit, 100),
        "page": 1,
        "sparkline": "false",
    }
    try:
        response = session.get(source_url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        rows = []
        for item in data:
            symbol = str(item.get("symbol", "")).upper()
            name = str(item.get("name", symbol))
            candidate_price_ticker = f"{symbol}-USD"
            stable = is_stablecoin_like(candidate_price_ticker, name)
            source_asset_id = str(item.get("id", "")).strip()
            rows.append(
                _base_row(
                    ticker=candidate_price_ticker,
                    name=name,
                    sleeve="crypto_top100",
                    region="Global",
                    country="Global",
                    exchange="Crypto",
                    currency="USD",
                    asset_type="crypto",
                    market_cap_usd=item.get("market_cap", ""),
                    market_cap_rank=item.get("market_cap_rank", ""),
                    investable=False,
                    signal_only=True,
                    include=not stable,
                    proxy_type="unverified_yahoo_crypto_symbol_candidate",
                    source_method="api_market_cap_enriched",
                    source="CoinGecko coins markets API",
                    source_url=source_url,
                    data_provider="CoinGecko",
                    source_asset_id=source_asset_id,
                    price_provider="Yahoo Finance",
                    price_ticker=candidate_price_ticker,
                    price_ticker_verified=False,
                    price_mapping_method="unverified_symbol_concatenation",
                    as_of_date=as_of,
                    notes=(
                        f"CoinGecko ID={source_asset_id or 'unavailable'}; market-cap "
                        f"API row retrieved {as_of}; stable_like={stable}; Yahoo price "
                        "mapping is unverified and therefore not investable."
                    ),
                )
            )
        return rows
    except Exception as exc:
        _issue(issues, "crypto_top100", source_url, "source_fetch_failed", str(exc))
        return []


def _commodity_rows(as_of: str) -> list[dict[str, Any]]:
    return [
        _base_row(
            ticker=ticker,
            name=name,
            sleeve="commodity_real_assets",
            region="Global",
            country="United States",
            exchange="NYSE Arca",
            currency="USD",
            asset_type="proxy",
            source="Yahoo Finance quote page",
            source_url=url,
            proxy_type=f"{proxy} ETF/fund proxy",
            source_method="manual_review_required",
            as_of_date=as_of,
            notes=f"Documented commodity proxy retrieved {as_of}; ETF/fund proxy differs from spot commodity.",
        )
        for ticker, name, proxy, url in COMMODITY_PROXIES
    ]


def _bond_rows(as_of: str) -> list[dict[str, Any]]:
    return [
        _base_row(
            ticker=ticker,
            name=name,
            sleeve="defensive_bonds_cash",
            region="North America",
            country="United States",
            exchange="NYSE Arca",
            currency="USD",
            asset_type="proxy",
            source="Yahoo Finance quote page",
            source_url=url,
            proxy_type=category,
            source_method="manual_review_required",
            as_of_date=as_of,
            notes=f"Documented defensive bond/cash proxy retrieved {as_of}; duration/risk category={category}.",
        )
        for ticker, name, category, url in BOND_PROXIES
    ]


def _write_source_files(
    source_dir: Path, rows_by_file: dict[str, list[dict[str, Any]]]
) -> None:
    for filename, rows in rows_by_file.items():
        pd.DataFrame(rows, columns=SOURCE_COLUMNS).drop_duplicates("ticker").to_csv(
            source_dir / filename, index=False
        )


def _write_compatibility_files(
    source_dir: Path, rows_by_file: dict[str, list[dict[str, Any]]]
) -> None:
    mapping = {
        "us_candidates.csv": [
            "nasdaq_top100_candidates.csv",
            "nyse_top100_candidates.csv",
        ],
        "europe_candidates.csv": [
            "europe_top100_candidates.csv",
            "germany_top100_candidates.csv",
        ],
        "uk_candidates.csv": ["uk_top100_candidates.csv"],
        "turkey_candidates.csv": ["turkey_top100_candidates.csv"],
        "china_candidates.csv": ["china_hk_top100_candidates.csv"],
        "japan_candidates.csv": ["japan_top100_candidates.csv"],
    }
    for filename, inputs in mapping.items():
        rows = [
            row for source_file in inputs for row in rows_by_file.get(source_file, [])
        ]
        pd.DataFrame(rows, columns=SOURCE_COLUMNS).drop_duplicates("ticker").to_csv(
            source_dir / filename, index=False
        )


def _write_reports(
    output_dir: Path,
    rows_by_file: dict[str, list[dict[str, Any]]],
    issues: list[dict[str, Any]],
) -> None:
    frames = [
        pd.DataFrame(rows, columns=SOURCE_COLUMNS) for rows in rows_by_file.values()
    ]
    combined = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=SOURCE_COLUMNS)
    )
    summary = combined.groupby("sleeve", as_index=False).agg(
        rows=("ticker", "count"),
        included=("include", "sum"),
        investable=("investable", "sum"),
    )
    summary.to_csv(
        output_dir / "real_global_universe_population_summary.csv", index=False
    )
    pd.DataFrame(
        issues, columns=["sleeve", "source_url", "issue", "detail", "severity"]
    ).to_csv(output_dir / "real_global_universe_population_issues.csv", index=False)
    cap = combined.copy()
    cap["market_cap_present"] = pd.to_numeric(
        cap["market_cap_usd"], errors="coerce"
    ).notna()
    cap["market_cap_rank_present"] = pd.to_numeric(
        cap["market_cap_rank"], errors="coerce"
    ).notna()
    cap.groupby("sleeve", as_index=False).agg(
        rows=("ticker", "count"),
        market_cap_rows=("market_cap_present", "sum"),
        market_cap_rank_rows=("market_cap_rank_present", "sum"),
    ).to_csv(output_dir / "real_global_universe_market_cap_coverage.csv", index=False)
    combined.assign(
        source_url_present=combined["source_url"].astype(str).str.len().gt(0)
    ).groupby("sleeve", as_index=False).agg(
        rows=("ticker", "count"),
        source_urls=("source_url_present", "sum"),
        source_methods=("source_method", lambda s: ", ".join(sorted(set(map(str, s))))),
    ).to_csv(
        output_dir / "real_global_universe_source_coverage.csv", index=False
    )


def _us_symbol(value: Any) -> str:
    return str(value).strip().replace(".", "-")


def _suffix(value: str, suffix: str) -> str:
    value = value.strip()
    return value if value.endswith(suffix) else f"{value}{suffix}"


def _hk_symbol(value: str) -> str:
    match = re.search(r"(\d+)", value)
    if not match:
        return value.strip()
    return f"{int(match.group(1)):04d}.HK"


if __name__ == "__main__":
    sys.exit(main())
