-- Section 1.1: Create the assignment database with CAT timezone + TimescaleDB
-- Run as superuser against the maintenance DB.

DROP DATABASE IF EXISTS energy_grid;
CREATE DATABASE energy_grid WITH TEMPLATE = template0 ENCODING = 'UTF8';

\c energy_grid

-- Enable TimescaleDB extension in this DB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Set session + DB default time zone to Africa/Kigali (CAT, UTC+02:00)
ALTER DATABASE energy_grid SET timezone TO 'Africa/Kigali';
SET TIME ZONE 'Africa/Kigali';

-- Verification
SELECT current_database() AS db,
       current_setting('TimeZone') AS session_tz,
       (SELECT extversion FROM pg_extension WHERE extname='timescaledb') AS timescaledb_version,
       version() AS postgres_version;
