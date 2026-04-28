-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create main table
CREATE TABLE IF NOT EXISTS adsb (
    t TIMESTAMP WITH TIME ZONE,
    hex TEXT,
    flight TEXT,
    alt BIGINT,
    gs DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    bearing DOUBLE PRECISION,
    registration TEXT,
    typecode TEXT,
    category TEXT,
    military BOOLEAN
);

-- Create temporary loading table
CREATE TABLE IF NOT EXISTS adsb_temp (
    t DOUBLE PRECISION,
    hex TEXT,
    flight TEXT,
    squawk TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    alt BIGINT,
    gs DOUBLE PRECISION,
    type INTEGER
);

-- Create modes table for aircraft metadata
CREATE TABLE IF NOT EXISTS modes (
    hex TEXT PRIMARY KEY,
    registration TEXT,
    typecode TEXT,
    category TEXT,
    military BOOLEAN,
    owner TEXT,
    aircraft TEXT
);

-- Create indexes on main table (idempotent)
CREATE INDEX IF NOT EXISTS adsb_t_idx ON adsb (t);
CREATE INDEX IF NOT EXISTS adsb_hex_idx ON adsb (hex);
CREATE INDEX IF NOT EXISTS adsb_geom_idx ON adsb USING GIST (geom);
CREATE INDEX IF NOT EXISTS adsb_category_idx ON adsb (category);
