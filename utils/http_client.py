"""
Defensive HTTP networking client using pure Python standard library.
Handles redirects, custom headers, SSL verification, and status validation.
"""

import json
import logging
import urllib.request
import urllib.error
from config import USER_AGENT, REQUEST_TIMEOUT

logger = logging.getLogger("etl_worker")


def fetch_url(url, timeout=REQUEST_TIMEOUT):
    """
    Fetches raw bytes from a URL with automatic redirect handling and error reporting.
    """
    logger.info("Requesting remote resource: %s", url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            logger.info("Successfully fetched %d bytes from %s (HTTP %s)", len(data), url, response.status)
            return data
    except urllib.error.HTTPError as e:
        logger.error("HTTP error %d fetching %s: %s", e.code, url, e.reason)
        raise
    except urllib.error.URLError as e:
        logger.error("Network connection error reaching %s: %s", url, e.reason)
        raise


def post_json(endpoint_url, payload, token, timeout=REQUEST_TIMEOUT):
    """
    Sends structured JSON data to the target ingestion API endpoint with Bearer token authentication.
    """
    logger.info("Transmitting payload (%s) to %s", payload.get("slug", "unknown"), endpoint_url)
    json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        endpoint_url,
        data=json_bytes,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode("utf-8")
            logger.info("Receiver API responded with HTTP %d: %s", response.status, res_body)
            try:
                return json.loads(res_body)
            except Exception:
                return {"raw_response": res_body, "status_code": response.status}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        logger.error("Ingestion endpoint rejected transmission with HTTP %d: %s", e.code, err_msg)
        raise RuntimeError(f"API rejection HTTP {e.code}: {err_msg}")
    except urllib.error.URLError as e:
        logger.error("Network error transmitting to %s: %s", endpoint_url, e.reason)
        raise
