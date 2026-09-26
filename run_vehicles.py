#!/usr/bin/env python3
"""
Fetch GTFS-Realtime vehicle positions for a city and POST to Django.
Trigger frequently (~30s feed cadence) via external cron → workflow_dispatch.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cities import CITIES, get_city
from config import DEFAULT_INGEST_KEY, DEFAULT_VEHICLES_ENDPOINT, VEHICLE_REQUEST_TIMEOUT
from gtfs_realtime import build_vehicles_payload
from http_client import fetch_bytes, post_json

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gtfs_ingest")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest GTFS-Realtime vehicles for a city.")
    parser.add_argument("--city", "-c", default="johor", help="City slug (e.g. johor) or 'all'")
    parser.add_argument("--endpoint", "-e", default=DEFAULT_VEHICLES_ENDPOINT)
    parser.add_argument("--token", "-t", default=DEFAULT_INGEST_KEY)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dump", type=str, default="")
    args = parser.parse_args()

    targets = list(CITIES.keys()) if args.city == "all" else [args.city]
    failures = 0

    for slug in targets:
        try:
            city = get_city(slug)
            logger.info("Vehicles ingest start city=%s url=%s", slug, city["vehicles_url"])
            pb = fetch_bytes(city["vehicles_url"], timeout=VEHICLE_REQUEST_TIMEOUT)
            payload = build_vehicles_payload(
                pb,
                city_slug=city["city_slug"],
                feed_id=city["feed_id"],
            )

            if args.dump:
                path = args.dump if len(targets) == 1 else f"{args.dump.rstrip('/')}/{slug}-vehicles.json"
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False)
                logger.info("Wrote dump %s", path)

            if args.dry_run:
                logger.info("Dry-run city=%s vehicles=%s", slug, payload["vehicle_count"])
                continue

            if not args.token:
                raise RuntimeError("INGEST_API_KEY / --token is required when not using --dry-run")

            result = post_json(args.endpoint, payload, args.token)
            logger.info("Vehicles ingest success city=%s result=%s", slug, result)
        except Exception:
            logger.exception("Vehicles ingest failed city=%s", slug)
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
