"""Defensive HTTP client (stdlib only) for fetch + authenticated JSON POST."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from config import POST_REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger("gtfs_ingest")


def fetch_bytes(url: str, timeout: int) -> bytes:
    logger.info("Fetching %s (timeout=%ss)", url, timeout)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            logger.info("Fetched %d bytes from %s (HTTP %s)", len(data), url, response.status)
            return data
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        logger.error("HTTP %s fetching %s: %s", exc.code, url, body)
        raise
    except urllib.error.URLError as exc:
        logger.error("Network error fetching %s: %s", url, exc.reason)
        raise


def post_json(endpoint_url: str, payload: dict, token: str, timeout: int = POST_REQUEST_TIMEOUT) -> dict:
    city = payload.get("city_slug", "unknown")
    logger.info("POSTing city=%s to %s", city, endpoint_url)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        endpoint_url,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            logger.info("Ingest API HTTP %s for city=%s (%d bytes response)", response.status, city, len(raw))
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw_response": raw, "status_code": response.status}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        logger.error("Ingest rejected city=%s HTTP %s: %s", city, exc.code, err[:1000])
        raise RuntimeError(f"API rejection HTTP {exc.code}: {err}") from exc
    except urllib.error.URLError as exc:
        logger.error("Network error POSTing to %s: %s", endpoint_url, exc.reason)
        raise
