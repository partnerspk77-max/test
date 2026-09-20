#!/usr/bin/env python3
"""
Malaysia Live Trains - Transit ETL Worker Runner.
Central CLI entrypoint to execute line extractors and transmit structured data to the web app.
Designed to run on GitHub Actions free runner or any independent cron server.
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone

# Ensure etl_worker root is in sys.path for both standalone execution and package imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_INGEST_ENDPOINT, DEFAULT_INGEST_KEY
from lines import EXTRACTORS

# Setup structured console logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("etl_worker")


def main():
    parser = argparse.ArgumentParser(
        description="Standalone Malaysian Transit ETL Worker (GitHub Actions Runner compatible)."
    )
    parser.add_argument(
        "--line", "-l",
        type=str,
        default="all",
        help="Line slug to process (e.g., 'mrt-kajang') or 'all'."
    )
    parser.add_argument(
        "--endpoint", "-e",
        type=str,
        default=DEFAULT_INGEST_ENDPOINT,
        help="Target MTrain ingestion API URL."
    )
    parser.add_argument(
        "--token", "-t",
        type=str,
        default=DEFAULT_INGEST_KEY,
        help="Bearer authorization token for MTrain API."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and validate data without transmitting over network."
    )

    args = parser.parse_args()

    start_time = datetime.now(timezone.utc)
    logger.info("=" * 65)
    logger.info("Starting Transit ETL Pipeline Execution")
    logger.info("Target Line: %s | Dry-run: %s", args.line, args.dry_run)
    logger.info("Target Endpoint: %s", args.endpoint)
    logger.info("=" * 65)

    # Determine which extractors to execute
    target_extractors = {}
    if args.line == "all":
        target_extractors = EXTRACTORS
    elif args.line in EXTRACTORS:
        target_extractors = {args.line: EXTRACTORS[args.line]}
    else:
        logger.error("Unknown line slug '%s'. Available lines: %s", args.line, list(EXTRACTORS.keys()))
        sys.exit(1)

    success_count = 0
    failure_count = 0

    for slug, ExtractorCls in target_extractors.items():
        logger.info("-" * 50)
        logger.info("Processing pipeline for: %s", slug)
        try:
            extractor = ExtractorCls(endpoint_url=args.endpoint, api_token=args.token)
            result = extractor.run(dry_run=args.dry_run)
            logger.info("Pipeline completed successfully for %s: %s", slug, result)
            success_count += 1
        except Exception as e:
            logger.exception("Pipeline failed for line '%s': %s", slug, e)
            failure_count += 1

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("=" * 65)
    logger.info(
        "ETL Execution Summary: %d succeeded, %d failed in %.2f seconds.",
        success_count, failure_count, duration
    )
    logger.info("=" * 65)

    if failure_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
