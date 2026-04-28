#!/usr/bin/env bash
# Run the Turnstone schema against an external DB (when using DATABASE_URL).
# Idempotent: safe to run multiple times (CREATE IF NOT EXISTS).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load docker/.env if DATABASE_URL not already set
if [ -z "$DATABASE_URL" ] && [ -f "$REPO_ROOT/docker/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$REPO_ROOT/docker/.env"
  set +a
fi

if [ -z "$DATABASE_URL" ]; then
  echo "Set DATABASE_URL (e.g. postgresql://user:pass@host:5432/adsb) or add it to docker/.env" >&2
  exit 1
fi

# Check PostGIS is available (required for geometry types)
if ! psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis;" 2>/dev/null; then
  echo "ERROR: PostGIS is not installed on your PostgreSQL server." >&2
  echo "Turnstone requires PostGIS for the adsb schema. Install it on the DB server, e.g.:" >&2
  echo "  • macOS (Homebrew):  brew install postgis" >&2
  echo "  • Ubuntu/Debian:     sudo apt install postgresql-16-postgis-3   # adjust 16 to your PG major version" >&2
  echo "  • Then re-run this script." >&2
  exit 1
fi

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$REPO_ROOT/docker/postgres/01_schema.sql"
echo "Schema applied."

if [ -f "$REPO_ROOT/data/modes.csv" ]; then
  echo "Loading modes.csv..."
  if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "\\copy modes FROM '$REPO_ROOT/data/modes.csv' WITH (FORMAT csv, DELIMITER ',', HEADER true)" 2>/dev/null; then
    echo "modes.csv loaded (7-column format)."
  else
    # 11-column augmented format: use staging and map into modes (c1=hex,c2=reg,c4=typecode,c9=category,c10=military,c6=owner,c8=aircraft)
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 << EOSQL
CREATE TEMP TABLE modes_stage (c1 text, c2 text, c3 text, c4 text, c5 text, c6 text, c7 text, c8 text, c9 text, c10 text, c11 text);
\\copy modes_stage FROM '$REPO_ROOT/data/modes.csv' WITH (FORMAT csv, DELIMITER ',', HEADER true);
INSERT INTO modes (hex, registration, typecode, category, military, owner, aircraft)
SELECT c1, c2, c4, c9, LOWER(COALESCE(c10,'')) IN ('t','true','1','yes'), c6, c8 FROM modes_stage
ON CONFLICT (hex) DO UPDATE SET
  registration = EXCLUDED.registration,
  typecode = EXCLUDED.typecode,
  category = EXCLUDED.category,
  military = EXCLUDED.military,
  owner = EXCLUDED.owner,
  aircraft = EXCLUDED.aircraft;
EOSQL
    echo "modes.csv loaded (11-column format)."
  fi
else
  echo "No data/modes.csv found; modes table is empty (optional)."
fi
