# Malaysia Live Trains - Standalone Transit ETL Worker

A high-performance, decoupled data extraction and ingestion pipeline designed to run on **GitHub Actions Free Runners** or external worker servers. It fetches official GTFS open transit data from `data.gov.my`, patches source data bugs, and pushes canonical JSON payloads to your main web application (`malaysia.metro-status.com`).

---

## Key Features

- **Zero External Dependencies**: Built with 100% Python Standard Library (`urllib.request`, `zipfile`, `csv`, `json`, `hmac`). Runs out of the box with zero `pip install`.
- **Decoupled Architecture**: Keeps heavy GTFS downloading and CSV parsing completely off your customer-facing web server.
- **GitHub Free Runner Ready**: Complete with a GitHub Action workflow ready to run on GitHub's free runners without using local CPU or memory.
- **External Cron Triggerable**: Easily triggered from external cron services (cron-job.org, EasyCron, Pipedream, Zapier) via GitHub's `repository_dispatch` API.
- **Defensive Bug Patches**: Automatically fixes upstream government GTFS data quirks:
  1. Route ID Mismatch (`stops.txt` uses `route_id = 'MRT'`, whereas `routes.txt` defines `'KGL'`).
  2. Strips UTF-8 Byte Order Marks (`\ufeffroute_id`) and maps short-code aliases.
  3. Drops corrupted serialized `[object Object]` geometry values and sanitizes lat/lon coordinates.

---

## 1. Quick Start (Running Locally)

```bash
# 1. Test extraction in dry-run mode (no network transmission):
python runner.py --line mrt-kajang --dry-run

# 2. Transmit to your local MTrain development server:
python runner.py \
  --line mrt-kajang \
  --endpoint http://127.0.0.1:8000/api/v1/ingest/line/ \
  --token mtrain-secret-etl-key-change-in-prod

# 3. Transmit to your production web app:
python runner.py \
  --line all \
  --endpoint https://malaysia.metro-status.com/api/v1/ingest/line/ \
  --token <YOUR_PRODUCTION_API_KEY>
```

---

## 2. Deploying as a Standalone GitHub Repository

You can deploy the contents of this folder as a separate public or private repository on GitHub:

```bash
cd scripts/etl_worker

# Initialize a new git repository
git init
git add .
git commit -m "feat: initial transit ETL worker runner"

# Create a new repository on GitHub (e.g. mal-trains-worker)
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_WORKER_REPO>.git
git branch -M main
git push -u origin main
```

---

## 3. Configuring GitHub Repository Secrets

Because your worker repository may be public, all API endpoints and security tokens are stored securely in **GitHub Encrypted Secrets**:

1. In your GitHub worker repository, navigate to:  
   **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**
2. Add the following two secrets:

| Secret Name | Example Value | Description |
| :--- | :--- | :--- |
| `INGEST_ENDPOINT` | `https://malaysia.metro-status.com/api/v1/ingest/line/` | The target Django API endpoint. |
| `INGEST_API_KEY` | `your-secret-key-configured-in-cpanel-env` | The Bearer token matching `INGEST_API_KEY` in Django. |

---

## 4. Triggering via External Cron (Outside of GitHub)

Instead of relying on GitHub's built-in scheduled actions (which can be delayed by hours during peak GitHub load), you can trigger the runner from an **external cron service** (such as [cron-job.org](https://cron-job.org), EasyCron, or a simple Linux server crontab) using GitHub's REST API.

### Step 1: Create a Fine-Grained Personal Access Token (PAT)
1. On GitHub, go to **Settings** ➔ **Developer settings** ➔ **Personal access tokens** ➔ **Fine-grained tokens** (or Classic Tokens).
2. Generate a token with **Actions: Read and write** permissions for your worker repository.

### Step 2: External HTTP POST Trigger Command
Send an authenticated HTTP POST request to GitHub's `dispatches` endpoint:

```bash
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: Bearer <YOUR_GITHUB_PAT>" \
  https://api.github.com/repos/<YOUR_USERNAME>/<YOUR_WORKER_REPO>/dispatches \
  -d '{"event_type": "trigger-etl"}'
```

GitHub immediately launches a free Ubuntu runner, pulls the latest code, extracts official GTFS data, patches it, and pushes structured data to your web app in ~5 to 10 seconds!

---

## 5. Malaysian GTFS Static Data Update Frequency

### How frequently does static transit data change?
- **Prasarana / Rapid Rail**: Typically updates static GTFS feeds **once every 1 to 3 months**, or when major timetable/frequency adjustments occur (e.g., adding train sets, festive schedule variations, or opening new stations).
- **KTMB (KTM Komuter & ETS)**: Updates approximately **2 to 4 times a year**.
- **ERL (KLIA Ekspres/Transit)**: Highly stable, typically updating **once or twice a year**.

### Recommended Cron Trigger Schedule
- **Daily Run (e.g. 03:00 AM UTC / 11:00 AM MYT)**:  
  Running the ETL once daily ensures you catch any official schedule or station updates immediately.
- **Quota Consumption**:  
  Each run takes approximately **8 seconds**. Over a 30-day month, daily runs consume **~4 minutes** of GitHub's free 2,000 monthly runner minutes (< 0.25% of your free allocation).

---

## 6. Project Structure

```
etl_worker/
├── .github/
│   └── workflows/
│       └── run_etl.yml        # GitHub Actions workflow (repository_dispatch & workflow_dispatch)
├── config.py                  # Environment configuration & endpoints
├── utils/
│   ├── http_client.py         # Defensive standard-library HTTP fetcher with retry logic
│   └── gtfs_parser.py         # In-memory ZIP/CSV reader with BOM stripping & safe typing
├── lines/
│   ├── base.py                # Abstract BaseTransitExtractor class
│   └── mrt_kajang.py          # MRT Kajang specific extractor & bug patches
├── runner.py                  # CLI orchestration entrypoint
├── requirements.txt           # Dependency declaration (Zero external packages)
├── .env.example               # Template for environment variables
└── README.md                  # Integration & deployment manual
```
