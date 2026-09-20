"""
Configuration settings for the Transit ETL Worker.
Reads environment variables (such as GitHub Actions Secrets) with sensible defaults.
"""

import os

# Default Ingestion API Endpoint and Authorization Secret
DEFAULT_INGEST_ENDPOINT = os.environ.get(
    "INGEST_ENDPOINT",
    "https://malaysia.metro-status.com/api/v1/ingest/line/"
)
DEFAULT_INGEST_KEY = os.environ.get("INGEST_API_KEY", "")

# Official Open Data Transit URLs
RAPID_RAIL_GTFS_URL = "https://api.data.gov.my/gtfs-static/prasarana?category=rapid-rail-kl"
RAPID_BUS_FEEDER_RT_URL = "https://api.data.gov.my/gtfs-realtime/vehicle-position/prasarana?category=rapid-bus-mrtfeeder"

# HTTP User-Agent for government open data gateways
USER_AGENT = "MalyTrains-TransitWorker/1.0 (+https://malaysia.metro-status.com)"

# Network Request Timeout (seconds)
REQUEST_TIMEOUT = 30
