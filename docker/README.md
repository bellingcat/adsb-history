# Docker — Turnstone ADS-B History

Run the app with **everything under the repo `data/` directory**. Restarts reuse that data (no automatic re-download; Postgres and backups persist).

| | URL |
|--|-----|
| Frontend | http://localhost:8080 |
| API | http://localhost:5000 |

**In this doc:** [Prerequisites](#prerequisites) · [Quick start](#quick-start) · [`data/` layout](#data-directory-layout) · [Download script](#globe_history-download-script) · [Environment](#environment-variables) · [Local Postgres](#local-postgres) · [External Postgres](#external-postgres) · [Manual extract](#manual-archive-extract)

---

## Prerequisites

- Docker with Compose v2
- **curl** and **jq** (heatmap download script)

---

## Quick start

All commands assume **repository root** as the working directory.

1. **Environment**

   ```bash
   cp docker/.env.example docker/.env
   ```

2. **Heatmap files** — run the download script (see [Globe_history download script](#globe_history-download-script) for options):

   ```bash
   mkdir -p data
   ./scripts/download-globe-history.sh data
   ```

   Note the extracted directory name under `data/` (e.g. `v2026.04.15-planes-readsb-prod-0`). Use it as `RELEASE_DIR` in the next step.

3. **Stack** (local Postgres — default):

   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

4. **Load heatmap** (replace `RELEASE_DIR`):

   ```bash
   docker compose -f docker/docker-compose.yml run --rm data-loading /data/RELEASE_DIR/heatmap
   ```

Loader paths are **inside the container**: host `data/` is mounted at `/data`, so use `/data/...`, not `data/...`.

For **external Postgres**, use the steps in [External Postgres](#external-postgres) instead of steps 3–4 as written above.

---

## Data directory layout

| Path | Purpose |
|------|--------|
| `data/<RELEASE_DIR>/` | Extracted [globe_history](https://github.com/adsblol/globe_history/releases) tree (includes `heatmap/` with tile binaries) |
| `data/pgdata/` | Local Postgres data (created on first run when using the default compose file) |
| `data/modes.csv` | Optional aircraft metadata (7- or 11-column CSV) |
| `data/firebase-key.json` | Optional; required only with Firebase auth (`docker-compose.firebase.yml`) |
| `data/query-history-backup.json` | Optional API query-history backup |

---

## Globe_history download script

Script: `./scripts/download-globe-history.sh [DATA_DIR]` (default `DATA_DIR` is `data`).

Source: [adsblol/globe_history releases](https://github.com/adsblol/globe_history/releases) — split archives (`.tar.aa`, `.tar.ab`, …).

**Interactive terminal:** fetches the full release list (paginated API), shows **prod-only** tags (`-planes-readsb-prod-`), then prompts for a selection:

| Input | Meaning |
|-------|--------|
| Index (newest = `1`) | e.g. `3`, `1,4,6`, or range `5-10` |
| One day | e.g. `2026.04.15` |
| Inclusive range | `2026.04.10..2026.04.15` or `2026.04.10-2026.04.15` |
| Empty line | Latest prod only |

Comma-separated tokens can be mixed (e.g. `1,2026.04.14,5-7`). Each chosen release is extracted to `data/<RELEASE_DIR>/`. Load all of them with one bulk `data-loading` run (default `/data`), or point the loader at a single `/data/<RELEASE_DIR>/heatmap`.

**Non-interactive** (no TTY / piped stdin): downloads the **latest prod** release only (CI-friendly).

---

## Environment variables

Compose reads **`docker/.env`** (from `docker/.env.example`). Common entries:

| Variable | Role |
|----------|------|
| `POSTGRES_*` | Local Postgres user, password, database, port |
| `DB_*` | API database connection (defaults match Docker networking) |
| `DATABASE_URL` | If set, API and `data-loading` prefer this over `DB_*` — see [External Postgres](#external-postgres) |
| `DISABLE_AUTH`, `VITE_DISABLE_AUTH` | Set to `0` to enable Firebase; add `docker-compose.firebase.yml` and `data/firebase-key.json` |
| `VITE_API_BASE_URL` | Browser-visible API URL (default `http://localhost:5000`) |
| `QUERY_HISTORY_BACKUP_PATH` | Query-history backup path inside the API container |

---

## Local Postgres

**Start:**

```bash
docker compose -f docker/docker-compose.yml up -d
```

**Load heatmap:**

- **All releases under `data/`** (every `data/*/heatmap` that contains data; `data/pgdata` is skipped):  
  `docker compose -f docker/docker-compose.yml run --rm data-loading`
- **One release:**  
  `docker compose -f docker/docker-compose.yml run --rm data-loading /data/RELEASE_DIR/heatmap`

The loader expects each heatmap tree under **`heatmap/`** (per-day folders or flat files `0`–`47` / `00.bin.ttf`–`47.bin.ttf`).

---

## External Postgres

Use your own Postgres (hosted or local). The default Postgres service is not used; **`DATABASE_URL`** in `docker/.env` drives the API and `data-loading`.

1. Set `DATABASE_URL`, for example:  
   `postgresql://user:password@host:5432/adsb`

2. **PostGIS** is required (e.g. `brew install postgis` or your distro’s PostGIS package).

3. Initialize schema (idempotent, once):

   ```bash
   ./scripts/init-external-db.sh
   ```

   The script reads `docker/.env` when `DATABASE_URL` is not already in the environment.

4. Start the stack with the external-DB override:

   ```bash
   docker compose -f docker/docker-compose.yml -f docker/docker-compose.external-db.yml up -d
   ```

5. Load heatmap:

   ```bash
   docker compose -f docker/docker-compose.yml -f docker/docker-compose.external-db.yml run --rm data-loading /data/RELEASE_DIR/heatmap
   ```

---

## Manual archive extract

If you download split `.tar.*` parts from GitHub by hand:

```bash
mkdir -p data/<release-dir>
cat v*.tar.aa v*.tar.ab | tar -xf - -C data/<release-dir>
docker compose -f docker/docker-compose.yml run --rm data-loading /data/<release-dir>/heatmap
```

Adjust the final `docker compose` line if you use the external-DB compose files.

---

## Cheat sheet

- **One data root:** `data/` for heatmap extracts, optional `modes.csv`, Firebase key, query backup, and local Postgres (`data/pgdata/`).
- **Default restart:**  
  `docker compose -f docker/docker-compose.yml up -d`
- **With external DB:** add `-f docker/docker-compose.external-db.yml`.
- **With Firebase auth:** add `-f docker/docker-compose.firebase.yml` and configure `data/firebase-key.json`.
- **New heatmap:** extract under `data/`, then either bulk `run --rm data-loading` or one release: `run --rm data-loading /data/<dir>/heatmap`.
