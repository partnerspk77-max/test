#!/usr/bin/env python3
"""
Fetch GTFS static for a city and POST the compact catalog to Django.
Intended for GitHub Actions (workflow_dispatch or schedule) triggered by external cron.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cities import CITIES, get_city
from config import DEFAULT_INGEST_KEY, DEFAULT_STATIC_ENDPOINT, STATIC_REQUEST_TIMEOUT
from gtfs_static import build_static_payload
from http_client import fetch_bytes, post_json

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gtfs_ingest")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest GTFS static catalog for a city.")
    parser.add_argument("--city", "-c", default="johor", help="City slug (e.g. johor) or 'all'")
    parser.add_argument("--endpoint", "-e", default=DEFAULT_STATIC_ENDPOINT)
    parser.add_argument("--token", "-t", default=DEFAULT_INGEST_KEY)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dump", type=str, default="", help="Optional path to write JSON payload")
    args = parser.parse_args()

    targets = list(CITIES.keys()) if args.city == "all" else [args.city]
    failures = 0

    for slug in targets:
        try:
            city = get_city(slug)
            logger.info("Static ingest start city=%s url=%s", slug, city["static_url"])
            zip_bytes = fetch_bytes(city["static_url"], timeout=STATIC_REQUEST_TIMEOUT)
            payload = build_static_payload(
                zip_bytes,
                city_slug=city["city_slug"],
                city_name=city["city_name"],
                feed_id=city["feed_id"],
                attribution=city["attribution"],
                timezone_name=city["timezone"],
            )
            # Attach map defaults for the frontend (not from GTFS)
            payload["mode"] = city["mode"]
            payload["operator"] = city["operator"]
            payload["map_center"] = city["map_center"]
            payload["map_zoom"] = city["map_zoom"]

            if args.dump:
                path = args.dump if len(targets) == 1 else f"{args.dump.rstrip('/')}/{slug}.json"
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False)
                logger.info("Wrote dump %s", path)

            if args.dry_run:
                logger.info(
                    "Dry-run city=%s routes=%s stops=%s",
                    slug,
                    payload["stats"]["route_count"],
                    payload["stats"]["stop_count"],
                )
                continue

            if not args.token:
                raise RuntimeError("INGEST_API_KEY / --token is required when not using --dry-run")

            result = post_json(args.endpoint, payload, args.token)
            logger.info("Static ingest success city=%s result=%s", slug, result)
        except Exception:
            logger.exception("Static ingest failed city=%s", slug)
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
