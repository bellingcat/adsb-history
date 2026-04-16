# Docker — Turnstone ADS-B History

Run the full stack with **all data under the repo `data/` folder**. Restarts use existing data (no re-download; DB and backups persist).

**URLs:** Frontend → http://localhost:8080 · API → http://localhost:5000

---

## Prerequisites

- Docker (Compose v2)
- **jq** (for the download script)
- From repo root: `cp docker/.env.example docker/.env`

---

## Quick start

### 1. Get heatmap data

```bash
mkdir -p data
./scripts/download-globe-history.sh data
```

The script prints the release dir (e.g. `v2026.03.10-planes-readsb-staging-0`). Use it as **RELEASE_DIR** below.

### 2. Choose database: local or external

| Use case | Start stack | Load heatmap |
|----------|-------------|--------------|
| **Local Postgres** (default) | `docker compose -f docker/docker-compose.yml up -d` | `docker compose -f docker/docker-compose.yml run --rm data-loading /data/RELEASE_DIR/heatmap` |
| **External DB** (`DATABASE_URL` in `docker/.env`) | See [External database](#external-database) | Same `run --rm data-loading /data/RELEASE_DIR/heatmap` with external compose (see below) |

**Example** (local Postgres, release dir `v2026.03.10-planes-readsb-staging-0`):

```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml run --rm data-loading /data/v2026.03.10-planes-readsb-staging-0/heatmap
```

Paths for the loader are **inside the container**: host `data/` is mounted at `/data`, so use `/data/RELEASE_DIR/heatmap`, not `data/RELEASE_DIR/heatmap`.

---

## Data folder

Everything persistent lives under **`data/`** (one place to back up or move):

| Path | Purpose |
|------|--------|
| `data/<RELEASE_DIR>/` | Extracted globe_history (e.g. `heatmap/` with `00.bin.ttf` … `47.bin.ttf`) |
| `data/pgdata/` | Postgres data (created on first run with local Postgres) |
| `data/modes.csv` | Optional aircraft metadata (7- or 11-column CSV) |
| `data/firebase-key.json` | Optional; only if using Firebase auth (use `-f docker/docker-compose.firebase.yml`) |
| `data/query-history-backup.json` | Optional; local query history backup |

---

## Environment

Compose uses **`docker/.env`** (copy from `docker/.env.example`). Main variables:

| Variable | Purpose |
|----------|--------|
| `POSTGRES_*` | Local Postgres (user, password, db, port) |
| `DB_*` | API DB connection (defaults work for Docker) |
| `DATABASE_URL` | If set, API and data-loading use this instead of `DB_*`; use with [external DB](#external-database) |
| `DISABLE_AUTH`, `VITE_DISABLE_AUTH` | Set to `0` to enable Firebase; add `-f docker/docker-compose.firebase.yml` and ensure `data/firebase-key.json` exists |
| `VITE_API_BASE_URL` | API URL seen by the browser (default `http://localhost:5000`) |
| `QUERY_HISTORY_BACKUP_PATH` | Path inside API container for backup file |

---

## Loading heatmap data

- **Default:** `docker compose -f docker/docker-compose.yml run --rm data-loading` processes `/data` (all under `data/`).
- **Single release:** `... run --rm data-loading /data/RELEASE_DIR/heatmap`

Heatmap source: [globe_history](https://github.com/adsblol/globe_history/releases) (split tar: `.tar.aa`, `.tar.ab`, …). The loader accepts the **heatmap** subfolder (files `0`–`47` or `00.bin.ttf`–`47.bin.ttf`).

**Manual extract:** download split parts from the [releases](https://github.com/adsblol/globe_history/releases) page, then:

```bash
mkdir -p data/<release-dir>
cat v*.tar.aa v*.tar.ab | tar -xf - -C data/<release-dir>
docker compose -f docker/docker-compose.yml run --rm data-loading /data/<release-dir>/heatmap
```

---

## External database

Use your own Postgres (e.g. cloud or host). No local Postgres container is run; API and data-loading use **`DATABASE_URL`** from `docker/.env`.

1. **Set `DATABASE_URL`** in `docker/.env`, e.g.  
   `DATABASE_URL=postgresql://user:password@host:5432/adsb`

2. **Create schema and optional modes** (once, idempotent):

   ```bash
   ./scripts/init-external-db.sh
   ```

   The script uses `docker/.env` if `DATABASE_URL` is not already set. Your DB must have **PostGIS** (e.g. `brew install postgis` or `apt install postgresql-16-postgis-3`).

3. **Start stack with external-DB override:**

   ```bash
   docker compose -f docker/docker-compose.yml -f docker/docker-compose.external-db.yml up -d
   ```

4. **Load heatmap** (paths as in [Loading heatmap data](#loading-heatmap-data)):

   ```bash
   docker compose -f docker/docker-compose.yml -f docker/docker-compose.external-db.yml run --rm data-loading /data/RELEASE_DIR/heatmap
   ```

---

## Summary

- **One data dir:** `data/` for heatmap, Postgres (`data/pgdata/`), modes, Firebase key, query-history backup.
- **Restart:** `docker compose -f docker/docker-compose.yml up -d` (or with `-f docker/docker-compose.external-db.yml` if using external DB; add `-f docker/docker-compose.firebase.yml` if using Firebase auth).
- **New heatmap:** run the data-loading container pointing at `/data/<path>/heatmap` as above.
