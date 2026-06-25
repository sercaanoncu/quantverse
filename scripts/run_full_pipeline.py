"""Run QuantVerse end-to-end and generate the PDF report."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from project.pipeline import PipelineConfig, run_full_pipeline
from project.reporting.pdf_report import generate_pdf_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run QuantVerse full pipeline")
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--skip-pdf", action="store_true")
    args = parser.parse_args()

    log_dir = Path("reports/run_logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "latest_run.log", mode="w", encoding="utf-8"),
        ],
    )
    config = PipelineConfig.from_yaml(args.config)
    config = replace(
        config,
        start_date=args.start_date or config.start_date,
        end_date=args.end_date if args.end_date is not None else config.end_date,
    )

    metadata = run_full_pipeline(config)
    print(metadata)

    if not args.skip_pdf:
        pdf_path = generate_pdf_report(output_path=config.pdf_output_path)
        print(f"PDF report written to: {pdf_path}")


if __name__ == "__main__":
    main()
