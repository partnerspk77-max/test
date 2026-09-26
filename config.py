"""
Configuration for the GTFS ingest worker (GitHub Actions / external cron).
Secrets are injected via GitHub Actions repository secrets or environment variables.
"""

import os

# Django application ingest endpoints (override per environment)
DEFAULT_BASE_URL = os.environ.get(
    "INGEST_BASE_URL",
    "https://malaysia.metro-status.com",
).rstrip("/")

DEFAULT_STATIC_ENDPOINT = os.environ.get(
    "INGEST_STATIC_ENDPOINT",
    f"{DEFAULT_BASE_URL}/api/v1/ingest/city/static/",
)
DEFAULT_VEHICLES_ENDPOINT = os.environ.get(
    "INGEST_VEHICLES_ENDPOINT",
    f"{DEFAULT_BASE_URL}/api/v1/ingest/city/vehicles/",
)
DEFAULT_INGEST_KEY = os.environ.get("INGEST_API_KEY", "")

# Official Malaysia Open API feeds
USER_AGENT = os.environ.get(
    "GTFS_USER_AGENT",
    "MalyTrains-GTFSIngest/1.0 (+https://malaysia.metro-status.com)",
)

# Static zip can exceed 2MB and be slow; vehicle protobuf is small.
STATIC_REQUEST_TIMEOUT = int(os.environ.get("STATIC_REQUEST_TIMEOUT", "180"))
VEHICLE_REQUEST_TIMEOUT = int(os.environ.get("VEHICLE_REQUEST_TIMEOUT", "30"))
POST_REQUEST_TIMEOUT = int(os.environ.get("POST_REQUEST_TIMEOUT", "60"))

# Attribution (CC BY 4.0 — required for redistribution of feed data)
DEFAULT_ATTRIBUTION = (
    "Transit data © data.gov.my / BAS.MY operators, licensed under CC BY 4.0. "
    "Live vehicle positions via GTFS-Realtime."
)
