"""Public QuantVerse package alias.

The historical internal package is `project`. New user-facing code can import
the production entry points from `quantverse` without breaking existing imports.
"""

from project.pipeline import PipelineConfig, run_full_pipeline

__all__ = ["PipelineConfig", "run_full_pipeline"]
