"""
Base Abstract Extractor for Malaysian Transit Lines.
Defines the standard contract for line extractors, ensuring consistency and clean error handling.
"""

import abc
import logging
from utils.http_client import post_json

logger = logging.getLogger("etl_worker")


class BaseTransitExtractor(abc.ABC):
    """
    Abstract base class for all transit line ETL pipelines.
    Subclasses implement line-specific GTFS filtering, bug patching, and metadata enrichment.
    """
    slug = ""
    name = ""

    def __init__(self, endpoint_url=None, api_token=None):
        self.endpoint_url = endpoint_url
        self.api_token = api_token

    @abc.abstractmethod
    def extract(self):
        """
        Extracts, patches, and builds the canonical line dictionary payload.
        Returns: dict
        """
        pass

    def run(self, dry_run=False):
        """
        Executes the line pipeline. If dry_run is True, skips transmission.
        """
        logger.info("Executing ETL pipeline for line: %s (%s)", self.name, self.slug)
        payload = self.extract()

        if not payload or not isinstance(payload, dict):
            raise ValueError(f"Extractor for '{self.slug}' produced an empty or invalid payload.")

        if dry_run:
            logger.info("Dry-run flag active: Payload generated successfully without sending to API.")
            return {"status": "dry-run", "slug": self.slug, "stations_count": len(payload.get("stations", []))}

        if not self.endpoint_url:
            raise ValueError("Target ingestion endpoint URL is not configured.")
        if not self.api_token:
            raise ValueError("Ingestion API Bearer token is not configured.")

        response = post_json(self.endpoint_url, payload, self.api_token)
        return response
