"""
QuantVerse Data Pipeline
========================
Multi-asset data ingestion, cleaning, and processing.
"""

from .universe import AssetUniverse, AssetClass
from .fetcher import DataFetcher
from .processor import DataProcessor

__all__ = ["AssetUniverse", "AssetClass", "DataFetcher", "DataProcessor"]
