"""City feed registry for multi-city GTFS ingest."""

from __future__ import annotations

from config import DEFAULT_ATTRIBUTION

# Add new Malaysian cities here as feeds become available.
CITIES: dict[str, dict] = {
    "johor": {
        "city_slug": "johor",
        "city_name": "Johor Bahru",
        "feed_id": "mybas-johor",
        "mode": "bus",
        "operator": "BAS.MY",
        "static_url": "https://api.data.gov.my/gtfs-static/mybas-johor",
        "vehicles_url": "https://api.data.gov.my/gtfs-realtime/vehicle-position/mybas-johor",
        "timezone": "Asia/Kuala_Lumpur",
        "attribution": DEFAULT_ATTRIBUTION,
        # Approximate map center for Leaflet default view
        "map_center": [1.4927, 103.7414],
        "map_zoom": 11,
    },
}


def get_city(city_slug: str) -> dict:
    city = CITIES.get(city_slug)
    if not city:
        raise KeyError(f"Unknown city_slug '{city_slug}'. Available: {sorted(CITIES.keys())}")
    return city
