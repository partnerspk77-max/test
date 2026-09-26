"""GTFS-Realtime vehicle-position protobuf → compact city payload."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("gtfs_ingest")


def build_vehicles_payload(
    protobuf_bytes: bytes,
    *,
    city_slug: str,
    feed_id: str,
) -> dict:
    try:
        from google.transit import gtfs_realtime_pb2
    except ImportError as exc:
        raise RuntimeError(
            "gtfs-realtime-bindings is required. Install workers/gtfs-ingest/requirements.txt"
        ) from exc

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(protobuf_bytes)

    vehicles = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        if not v.HasField("position"):
            continue

        trip = v.trip if v.HasField("trip") else None
        vehicle = v.vehicle if v.HasField("vehicle") else None
        pos = v.position

        item = {
            "id": entity.id or (vehicle.id if vehicle and vehicle.id else ""),
            "vehicle_id": vehicle.id if vehicle and vehicle.id else "",
            "label": vehicle.label if vehicle and vehicle.label else "",
            "trip_id": trip.trip_id if trip and trip.trip_id else "",
            "route_id": trip.route_id if trip and trip.route_id else "",
            "start_date": trip.start_date if trip and trip.start_date else "",
            "lat": round(pos.latitude, 6),
            "lon": round(pos.longitude, 6),
            "timestamp": int(v.timestamp) if v.HasField("timestamp") else int(feed.header.timestamp or 0),
        }
        if pos.HasField("bearing"):
            item["bearing"] = round(pos.bearing, 1)
        if pos.HasField("speed"):
            item["speed"] = round(pos.speed, 2)
        vehicles.append(item)

    synced_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "city_slug": city_slug,
        "feed_id": feed_id,
        "feed_timestamp": int(feed.header.timestamp or 0),
        "vehicle_count": len(vehicles),
        "vehicles": vehicles,
        "synced_at": synced_at,
    }
    with_route = sum(1 for v in vehicles if v.get("route_id"))
    logger.info(
        "Built vehicles payload city=%s count=%d with_route_id=%d",
        city_slug,
        len(vehicles),
        with_route,
    )
    return payload
