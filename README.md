# GTFS Ingest Worker

Standalone GitHub Actions–friendly worker that:

1. Fetches official Malaysia Open API GTFS static / realtime feeds
2. Parses and compresses them into SEO-ready JSON
3. POSTs into the Django app via authenticated ingest APIs

**No Django process, Redis, or native scheduler is required here.**  
Use an external cron platform to call `workflow_dispatch` on the Actions workflows.

## Layout

| Path | Role |
|------|------|
| `cities.py` | Multi-city feed registry (Johor first) |
| `run_static.py` | Daily/hourly static catalog ingest |
| `run_vehicles.py` | Frequent vehicle-position ingest (~30s feed) |
| `gtfs_static.py` / `gtfs_realtime.py` | Parsers |
| `http_client.py` | Fetch + Bearer POST |

## Local dry-run

```bash
cd workers/gtfs-ingest
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python run_vehicles.py --city johor --dry-run --dump /tmp/johor-vehicles.json
python run_static.py --city johor --dry-run --dump /tmp/johor-static.json
```

## GitHub secrets

| Secret | Purpose |
|--------|---------|
| `INGEST_API_KEY` | Bearer token matching Django `INGEST_API_KEY` |
| `INGEST_BASE_URL` | Optional; default `https://malaysia.metro-status.com` |

## Trigger from external cron

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_PAT" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows/gtfs-vehicles-ingest.yml/dispatches \
  -d '{"ref":"main","inputs":{"city":"johor"}}'
```

## Attribution

Feed metadata is CC BY 4.0. The site must display attribution (worker embeds an attribution string in static payloads).
