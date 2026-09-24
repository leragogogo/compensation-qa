# compensation-qa

Rule-based QA framework for German compensation-area registers, with Brandenburg as the reference profile. It consists of:

* **Engine**: Python (`ekisqa/`) — rule pack, reference-data cache, live EKIS register client
* **CLI**: [Typer](https://typer.tiangolo.com/) (`cli/`)
* **Web backend**: [FastAPI](https://fastapi.tiangolo.com/) (`web/api/`)
* **Web frontend**: React + Vite + Leaflet (`web/frontend/`)

## Prerequisites

* [Python](https://www.python.org/) 3.11+
* [Node.js](https://nodejs.org/) + npm

## Setup

1. Clone repository
   ```bash
   git clone <repo-url>
   cd compensation-qa
   ```
2. Create and activate a virtual environment
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

Both the CLI and the web application share the same engine package, so this
step is common to either one. The sections below are independent — set up
whichever you actually want to run.

## CLI Setup

1. **Install dependencies**
   ```bash
   pip install -e .
   ```
2. **Run a command**
   ```bash
   ekis-qa validate --file fixture.gpkg --state BB --format html
   ```

   If successful you'll see, on stderr:
   ```console
   N findings: X errors, Y warnings, Z info.
   ```
   and the report written to stdout or `--output`, depending on the format.

### Commands

#### `ekis-qa update-reference`

Fetches a profile's reference datasets (state boundary, district boundaries, protected areas) from their live WFS sources and caches them locally as GeoPackages under `reference/<STATE>/`.

```bash
ekis-qa update-reference --state BB --all
```

| Option    | Required | Description                                    |
|-----------|----------|-------------------------------------------------|
| `--state` | yes      | Land code (e.g. `BB`).                          |
| `--all`   | yes      | Fetch every reference dataset configured for the profile. |

Run this once (and re-run periodically to refresh the cache) before `validate`, so that reference-dependent rules have data to check against. If it's skipped, those rules don't fail — they're gracefully reported as `Info`-severity "skipped" findings instead.

#### `ekis-qa validate`

Runs the full rule pack (core geometry rules + the profile's own rules) against a register export and writes a findings report.

```bash
ekis-qa validate --file fixture.gpkg --state BB --format html
```

| Option           | Default   | Description                                                                 |
|------------------|-----------|-------------------------------------------------------------------------------|
| `--file`         | *required*| Register export to validate: a `.gpkg` (with `Kompensation`/`Eingriff` layers), a directory of shapefiles, or a GML pair. |
| `--state`        | `BB`      | Land code — selects which profile (schema adapter + rule pack) to run.       |
| `--rules`        | all       | Comma-separated list of `Rule.category` values to restrict the run to (e.g. `Geometry,Completeness`). |
| `--format`       | `json`    | Report format: `json`, `html`, `gpkg`, or `geojson`.                          |
| `--output`, `-o` | stdout    | Where to write the report. Optional for `json`/`html` (prints to stdout if omitted); **required** for `gpkg`/`geojson`. |
| `--check-date`   | today     | ISO date (`YYYY-MM-DD`) to record on the report.                             |
| `--live-register`| off       | Fetch the live EKIS register over the network before validating, so register-overlap rules (e.g. duplicate/near-duplicate detection) can run. Off by default to keep `validate` fast and offline. |

Reference data (boundaries, protected areas) is read from the local cache written by `update-reference` — `validate` itself never fetches it.

##### Report formats

- **`json`** — the findings list plus run metadata (land code, check date, register fetch timestamp), as a single JSON document.
- **`html`** — a standalone, human-readable report (no external scripts/stylesheets) with one row per finding, sorted by severity.
- **`gpkg`** — a GeoPackage with two layers, `Kompensation` and `Eingriff`, each feature's original attributes plus `qa_status`/`qa_errors`/`qa_warnings` columns.
- **`geojson`** — the same augmented data as two GeoJSON files. `--output report` produces `report.kompensation.geojson` and `report.eingriff.geojson`.

##### Rule categories

Valid values for `--rules` (case-sensitive, matching `Rule.category`):

`Geometry`, `Completeness`, `DomainValidity`, `GeometricSemantic`, `ReferentialIntegrity`, `SpatialLegalConstraints`, `TechnicalDelivery`, `Temporal`

Passing an unknown category exits with code 2 and lists the valid ones.

##### Exit codes

| Code | Meaning                                                              |
|------|-----------------------------------------------------------------------|
| `0`  | Ran successfully, no Error-severity findings (Warnings/Infos don't affect this). |
| `1`  | Ran successfully, but at least one Error-severity finding was produced. |
| `2`  | Usage or configuration problem: unknown `--state`, file not found, unreadable/malformed input, unknown `--rules` category, or a missing required `--output`. |

### Example workflow

```bash
# One-time (and periodic refresh): cache Brandenburg's reference data.
ekis-qa update-reference --state BB --all

# Validate a register export, get a GeoPackage back for QGIS.
ekis-qa validate --file export.gpkg --state BB --format gpkg --output report.gpkg

# Quick human read of just the geometry rules, as HTML.
ekis-qa validate --file export.gpkg --state BB --rules Geometry --format html --output report.html
```

## Web Application Setup

A FastAPI backend (`web/api/main.py`) plus a React/Vite frontend (`web/frontend/`). The backend reuses the same validation pipeline as the CLI (`ekisqa/pipeline.py`). Backend and frontend run as two separate processes, in two terminals, both from the repo root.

### Backend Setup

1. **Install dependencies**
   ```bash
   pip install -e ".[web]"
   ```
2. **Start the backend server**
   ```bash
   uvicorn web.api.main:app --reload
   ```

   If successful you'll see:
   ```console
   INFO:     Uvicorn running on http://127.0.0.1:8000
   INFO:     Application startup complete.
   ```

   The API is available at: http://localhost:8000

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd web/frontend
   npm install
   ```
2. **Start the frontend server**
   ```bash
   npm run dev
   ```

   The application should be available at: http://localhost:5173

   By default the frontend talks to the backend at `http://localhost:8000` (override with a `VITE_API_BASE` env var). The backend's CORS is only configured to accept requests from `localhost:5173`/`127.0.0.1:5173`, so if you run the frontend on a different port, update `allow_origins` in `web/api/main.py`.

Currently the upload endpoint (`POST /api/validate`) only accepts `.gpkg` files — shapefile/GML/GeoJSON pairs aren't supported through the web UI yet, only via the CLI.

## Run Tests

```bash
pip install -e ".[dev,web]"
pytest
```

`web` is included because `tests/unit/test_web_api.py` exercises the FastAPI backend directly.
