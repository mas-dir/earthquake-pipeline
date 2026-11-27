"""Run the whole pipeline: fetch -> clean -> analyze, with a log file.

Usage:
    python src/pipeline.py

Every run appends to logs/pipeline.log, so you can check later whether
the scheduled daily run worked and, if not, why.
"""
import logging
import sys
import time
from pathlib import Path

import analyze
import clean
import fetch

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "logs" / "pipeline.log"


def setup_logging() -> logging.Logger:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("pipeline")


def run_step(log: logging.Logger, name: str, func, *args, retries: int = 3):
    """Run one step; retry a few times because internet requests can fail briefly."""
    for attempt in range(1, retries + 1):
        try:
            result = func(*args)
            log.info("%s: OK", name)
            return result
        except Exception as error:  # log any failure instead of crashing silently
            log.warning("%s: attempt %d/%d failed: %s", name, attempt, retries, error)
            if attempt == retries:
                raise
            time.sleep(30)


def main() -> int:
    log = setup_logging()
    log.info("=== Pipeline started ===")
    try:
        raw_path = run_step(log, "1. Fetch", fetch.run, 30, 4.0)
        log.info("Raw file: %s", raw_path.name)
        clean_path = run_step(log, "2. Clean", clean.run, retries=1)
        log.info("Clean file: %s", clean_path.name)
        run_step(log, "3. Analyze", analyze.run, retries=1)
    except Exception:
        log.exception("=== Pipeline FAILED ===")
        return 1
    log.info("=== Pipeline finished successfully ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
