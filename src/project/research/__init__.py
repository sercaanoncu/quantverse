"""Research extensions for QuantVerse."""

from .challenger import (
    ALLOWED_EVIDENCE_CLASSES,
    ALLOWED_FINAL_LABELS,
    ALLOWED_PROMOTION_DECISIONS,
    ALLOWED_RESEARCH_EVIDENCE_CLASSES,
    ChallengerConfig,
    run_champion_challenger_research,
)

__all__ = [
    "ALLOWED_EVIDENCE_CLASSES",
    "ALLOWED_FINAL_LABELS",
    "ALLOWED_PROMOTION_DECISIONS",
    "ALLOWED_RESEARCH_EVIDENCE_CLASSES",
    "ChallengerConfig",
    "run_champion_challenger_research",
]
