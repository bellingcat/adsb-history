-- Create database
CREATE DATABASE adsb;

-- Enable PostGIS
CREATE EXTENSION postgis;

-- Create main table
CREATE TABLE adsb (
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
CREATE TABLE adsb_temp (
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
CREATE TABLE modes (
    hex TEXT PRIMARY KEY,
    registration TEXT,
    manufacturer TEXT,
    typecode TEXT,
    type TEXT,
    owner TEXT,
    operator TEXT,
    aircraft TEXT,
    category TEXT,
    military BOOLEAN,
    year INTEGER
);

COPY modes FROM 'modes.csv' DELIMITER ',' CSV HEADER;

-- Create indexes
CREATE INDEX adsb_t_idx ON adsb (t);
CREATE INDEX adsb_hex_idx ON adsb (hex);
CREATE INDEX adsb_geom_idx ON adsb USING GIST (geom);
CREATE INDEX adsb_category_idx ON adsb (category);
