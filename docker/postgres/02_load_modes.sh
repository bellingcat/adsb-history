#!/bin/bash
set -e
if [ -f /docker-entrypoint-initdb.d/modes.csv ] && [ -s /docker-entrypoint-initdb.d/modes.csv ]; then
  if psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\copy modes FROM '/docker-entrypoint-initdb.d/modes.csv' WITH (FORMAT csv, DELIMITER ',', HEADER true)" 2>/dev/null; then
    echo "Loaded modes.csv (7-column format)"
  else
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" << 'EOSQL'
CREATE TEMP TABLE modes_stage (c1 text, c2 text, c3 text, c4 text, c5 text, c6 text, c7 text, c8 text, c9 text, c10 text, c11 text);
\copy modes_stage FROM '/docker-entrypoint-initdb.d/modes.csv' WITH (FORMAT csv, DELIMITER ',', HEADER true);
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
    echo "Loaded modes.csv (11-column format)"
  fi
else
  echo "No modes.csv found or file empty - modes table left empty."
fi
