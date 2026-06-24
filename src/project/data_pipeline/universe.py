"""
QuantVerse — Asset Universe Definitions
========================================
Defines the investable universe across multiple asset classes.
Provides metadata, groupings, and filtering capabilities.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import yaml
from pathlib import Path


@dataclass
class AssetClass:
    """Represents a group of assets within the same class."""

    name: str
    description: str
    tickers: List[str]
    investable: bool = True


@dataclass
class AssetUniverse:
    """
    Complete multi-asset investment universe.

    Manages the full set of assets across equities, crypto,
    commodities, fixed income, and REITs with metadata and
    filtering capabilities.
    """

    asset_classes: Dict[str, AssetClass] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config_path: str = "configs/base.yaml") -> "AssetUniverse":
        """Load universe from YAML configuration file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        universe = cls()
        for class_name, class_data in config.get("universe", {}).items():
            investable = bool(class_data.get("investable", class_name != "signals"))
            universe.asset_classes[class_name] = AssetClass(
                name=class_name,
                description=class_data.get("description", ""),
                tickers=class_data.get("tickers", []),
                investable=investable,
            )
        return universe

    @classmethod
    def default(cls) -> "AssetUniverse":
        """Create the default QuantVerse universe without config file."""
        universe = cls()

        universe.asset_classes = {
            "us_equity_sectors": AssetClass(
                name="us_equity_sectors",
                description="S&P 500 Sector ETFs",
                tickers=[
                    "XLK",
                    "XLF",
                    "XLE",
                    "XLV",
                    "XLI",
                    "XLC",
                    "XLY",
                    "XLP",
                    "XLRE",
                    "XLU",
                    "XLB",
                ],
            ),
            "international_equity": AssetClass(
                name="international_equity",
                description="International Equity ETFs",
                tickers=["EFA", "EEM", "VGK", "VPL", "INDA", "FXI"],
            ),
            "crypto": AssetClass(
                name="crypto",
                description="Major Cryptocurrencies",
                tickers=[
                    "BTC-USD",
                    "ETH-USD",
                    "SOL-USD",
                    "BNB-USD",
                    "ADA-USD",
                    "XRP-USD",
                ],
            ),
            "commodities": AssetClass(
                name="commodities",
                description="Commodity ETFs",
                tickers=["GLD", "SLV", "USO", "UNG", "DBA", "PPLT", "CPER"],
            ),
            "fixed_income": AssetClass(
                name="fixed_income",
                description="Bond ETFs",
                tickers=["TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "AGG"],
            ),
            "reits": AssetClass(
                name="reits",
                description="Real Estate Investment Trusts",
                tickers=["VNQ", "VNQI"],
            ),
            "signals": AssetClass(
                name="signals",
                description="Market Signal Indicators (not investable)",
                tickers=["^VIX", "^TNX", "^IRX", "DX-Y.NYB"],
                investable=False,
            ),
        }
        return universe

    @property
    def all_tickers(self) -> List[str]:
        """Get all tickers across all asset classes."""
        tickers = []
        for ac in self.asset_classes.values():
            tickers.extend(ac.tickers)
        return tickers

    @property
    def investable_tickers(self) -> List[str]:
        """Get only investable tickers (excludes signals like VIX)."""
        tickers = []
        for ac in self.asset_classes.values():
            if ac.investable:
                tickers.extend(ac.tickers)
        return tickers

    @property
    def signal_tickers(self) -> List[str]:
        """Get non-investable signal tickers."""
        tickers = []
        for ac in self.asset_classes.values():
            if not ac.investable:
                tickers.extend(ac.tickers)
        return tickers

    def get_tickers_by_class(self, class_name: str) -> List[str]:
        """Get tickers for a specific asset class."""
        if class_name not in self.asset_classes:
            raise ValueError(
                f"Unknown asset class: {class_name}. "
                f"Available: {list(self.asset_classes.keys())}"
            )
        return self.asset_classes[class_name].tickers

    def get_asset_class_map(self) -> Dict[str, str]:
        """Return a mapping of ticker -> asset class name."""
        mapping = {}
        for class_name, ac in self.asset_classes.items():
            for ticker in ac.tickers:
                mapping[ticker] = class_name
        return mapping

    def filter_by_classes(self, class_names: List[str]) -> List[str]:
        """Get tickers from selected asset classes only."""
        tickers = []
        for name in class_names:
            tickers.extend(self.get_tickers_by_class(name))
        return tickers

    def summary(self) -> str:
        """Print a summary of the universe."""
        lines = ["=" * 60, "QuantVerse Asset Universe", "=" * 60]
        total = 0
        for name, ac in self.asset_classes.items():
            count = len(ac.tickers)
            total += count
            status = "📊" if ac.investable else "📡"
            lines.append(f"  {status} {ac.description}: {count} assets")
            lines.append(f"     {', '.join(ac.tickers)}")
        lines.append("-" * 60)
        lines.append(
            f"  Total: {total} assets "
            f"({len(self.investable_tickers)} investable, "
            f"{len(self.signal_tickers)} signals)"
        )
        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    universe = AssetUniverse.default()
    print(universe.summary())
