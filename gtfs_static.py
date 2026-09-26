"""GTFS static ZIP → compact city payload for Django ingest."""

from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger("gtfs_ingest")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str, fallback: str = "item") -> str:
    text = (value or "").strip().lower()
    text = _SLUG_RE.sub("-", text).strip("-")
    return text or fallback


def _extract_tables(zip_bytes: bytes) -> dict[str, str]:
    tables: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            base = name.split("/")[-1]
            if ("__MACOSX" in name) or base.startswith("."):
                continue
            if not (base.endswith(".txt") or base.endswith(".csv")):
                continue
            raw = archive.read(name)
            tables[base] = raw.decode("utf-8-sig")
    logger.info("Extracted GTFS tables: %s", sorted(tables.keys()))
    return tables


def _parse_csv(text: str) -> list[dict]:
    if not text or not text.strip():
        return []
    reader = csv.DictReader(io.StringIO(text.strip()))
    reader.fieldnames = [((f or "").strip()) for f in (reader.fieldnames or [])]
    rows = []
    for row in reader:
        rows.append({k: (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k})
    return rows


def _unique_slugs(items: list[dict], id_key: str, name_keys: tuple[str, ...]) -> None:
    used: set[str] = set()
    for item in items:
        base_parts = [item.get(k, "") for k in name_keys if item.get(k)]
        base = slugify("-".join(base_parts) or item.get(id_key, ""), fallback=item.get(id_key, "item"))
        candidate = base
        n = 2
        while candidate in used:
            candidate = f"{base}-{n}"
            n += 1
        used.add(candidate)
        item["slug"] = candidate


def _build_route_stop_order(trips: list[dict], stop_times: list[dict]) -> dict[str, list[str]]:
    """
    For each route_id, pick the trip with the most stop_times and return ordered stop_ids.
    Keeps payload small while still supporting route detail pages.
    """
    trip_to_route = {t["trip_id"]: t["route_id"] for t in trips if t.get("trip_id") and t.get("route_id")}
    stops_by_trip: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for st in stop_times:
        trip_id = st.get("trip_id")
        stop_id = st.get("stop_id")
        if not trip_id or not stop_id or trip_id not in trip_to_route:
            continue
        try:
            seq = int(st.get("stop_sequence") or 0)
        except ValueError:
            seq = 0
        stops_by_trip[trip_id].append((seq, stop_id))

    best_trip_by_route: dict[str, tuple[int, str]] = {}
    for trip_id, seq_stops in stops_by_trip.items():
        route_id = trip_to_route[trip_id]
        count = len(seq_stops)
        prev = best_trip_by_route.get(route_id)
        if prev is None or count > prev[0]:
            best_trip_by_route[route_id] = (count, trip_id)

    route_stops: dict[str, list[str]] = {}
    for route_id, (_, trip_id) in best_trip_by_route.items():
        ordered = [sid for _, sid in sorted(stops_by_trip[trip_id], key=lambda x: x[0])]
        # de-dupe while preserving order
        seen: set[str] = set()
        deduped = []
        for sid in ordered:
            if sid not in seen:
                seen.add(sid)
                deduped.append(sid)
        route_stops[route_id] = deduped
    return route_stops


def _downsample_shapes(shapes: list[dict], max_points: int = 200) -> dict[str, list[list[float]]]:
    by_shape: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for row in shapes:
        sid = row.get("shape_id")
        if not sid:
            continue
        try:
            seq = int(row.get("shape_pt_sequence") or 0)
            lat = float(row.get("shape_pt_lat"))
            lon = float(row.get("shape_pt_lon"))
        except (TypeError, ValueError):
            continue
        by_shape[sid].append((seq, lat, lon))

    out: dict[str, list[list[float]]] = {}
    for sid, pts in by_shape.items():
        pts.sort(key=lambda x: x[0])
        coords = [[lat, lon] for _, lat, lon in pts]
        if len(coords) > max_points:
            step = max(1, len(coords) // max_points)
            coords = coords[::step]
            if coords[-1] != [pts[-1][1], pts[-1][2]]:
                coords.append([pts[-1][1], pts[-1][2]])
        out[sid] = coords
    return out


def build_static_payload(
    zip_bytes: bytes,
    *,
    city_slug: str,
    city_name: str,
    feed_id: str,
    attribution: str,
    timezone_name: str = "Asia/Kuala_Lumpur",
) -> dict:
    tables = _extract_tables(zip_bytes)
    agency_rows = _parse_csv(tables.get("agency.txt", ""))
    route_rows = _parse_csv(tables.get("routes.txt", ""))
    stop_rows = _parse_csv(tables.get("stops.txt", ""))
    trip_rows = _parse_csv(tables.get("trips.txt", ""))
    stop_time_rows = _parse_csv(tables.get("stop_times.txt", ""))
    shape_rows = _parse_csv(tables.get("shapes.txt", "")) if "shapes.txt" in tables else []

    agency = agency_rows[0] if agency_rows else {}
    routes = []
    for r in route_rows:
        route_id = r.get("route_id")
        if not route_id:
            continue
        short = r.get("route_short_name") or ""
        long = r.get("route_long_name") or ""
        routes.append(
            {
                "route_id": route_id,
                "short_name": short,
                "long_name": long,
                "desc": r.get("route_desc") or "",
                "type": int(r.get("route_type") or 3),
                "color": (r.get("route_color") or "C8102E").lstrip("#").upper(),
                "text_color": (r.get("route_text_color") or "FFFFFF").lstrip("#").upper(),
            }
        )
    _unique_slugs(routes, "route_id", ("short_name", "long_name"))

    stops = []
    for s in stop_rows:
        stop_id = s.get("stop_id")
        if not stop_id:
            continue
        try:
            lat = float(s.get("stop_lat"))
            lon = float(s.get("stop_lon"))
        except (TypeError, ValueError):
            continue
        stops.append(
            {
                "stop_id": stop_id,
                "name": s.get("stop_name") or stop_id,
                "code": s.get("stop_code") or "",
                "lat": round(lat, 6),
                "lon": round(lon, 6),
            }
        )
    _unique_slugs(stops, "stop_id", ("name", "code"))

    route_stops = _build_route_stop_order(trip_rows, stop_time_rows)

    # Prefer one shape_id per route from trips (most common)
    shape_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in trip_rows:
        rid = t.get("route_id")
        sid = t.get("shape_id")
        if rid and sid:
            shape_votes[rid][sid] += 1
    route_shape_id = {
        rid: max(votes.items(), key=lambda kv: kv[1])[0]
        for rid, votes in shape_votes.items()
        if votes
    }
    shape_coords = _downsample_shapes(shape_rows) if shape_rows else {}
    route_shapes = {
        rid: shape_coords[sid]
        for rid, sid in route_shape_id.items()
        if sid in shape_coords
    }

    # Attach shape + stop count onto routes
    stop_index = {s["stop_id"]: s for s in stops}
    for route in routes:
        rid = route["route_id"]
        ordered = route_stops.get(rid, [])
        route["stop_ids"] = ordered
        route["stop_count"] = len(ordered)
        if ordered and ordered[0] in stop_index:
            route["from_stop"] = stop_index[ordered[0]]["name"]
        if ordered and ordered[-1] in stop_index:
            route["to_stop"] = stop_index[ordered[-1]]["name"]
        if rid in route_shapes:
            route["shape"] = route_shapes[rid]

    synced_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "city_slug": city_slug,
        "city_name": city_name,
        "feed_id": feed_id,
        "timezone": timezone_name,
        "attribution": attribution,
        "agency": {
            "id": agency.get("agency_id") or feed_id,
            "name": agency.get("agency_name") or city_name,
            "url": agency.get("agency_url") or "",
            "timezone": agency.get("agency_timezone") or timezone_name,
        },
        "routes": routes,
        "stops": stops,
        "stats": {
            "route_count": len(routes),
            "stop_count": len(stops),
            "trip_count": len(trip_rows),
        },
        "synced_at": synced_at,
    }
    logger.info(
        "Built static payload city=%s routes=%d stops=%d trips=%d",
        city_slug,
        len(routes),
        len(stops),
        len(trip_rows),
    )
    return payload
