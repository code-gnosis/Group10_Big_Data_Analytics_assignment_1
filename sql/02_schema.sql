-- Section 1.2 — Three tables for the ingestion pipeline.
-- Run inside energy_grid database.

SET TIME ZONE 'Africa/Kigali';

-- --- 1. Pilot buffer table (plain, no hypertable) ----------------------
DROP TABLE IF EXISTS energy_live CASCADE;
CREATE TABLE energy_live (
    meter_id      BIGINT           NOT NULL,
    event_time    TIMESTAMPTZ      NOT NULL,
    received_time TIMESTAMPTZ      NOT NULL,
    power_kw      DOUBLE PRECISION NOT NULL,
    voltage_v     DOUBLE PRECISION NOT NULL,
    current_a     DOUBLE PRECISION NOT NULL,
    frequency_hz  DOUBLE PRECISION NOT NULL,
    energy_kwh    DOUBLE PRECISION NOT NULL
);  -- duplicates allowed at this stage

-- --- 2. Historical hypertable (one-day chunks) --------------------------
DROP TABLE IF EXISTS energy_readings CASCADE;
CREATE TABLE energy_readings (
    meter_id      BIGINT           NOT NULL,
    event_time    TIMESTAMPTZ      NOT NULL,
    received_time TIMESTAMPTZ      NOT NULL,
    power_kw      DOUBLE PRECISION NOT NULL,
    voltage_v     DOUBLE PRECISION NOT NULL,
    current_a     DOUBLE PRECISION NOT NULL,
    frequency_hz  DOUBLE PRECISION NOT NULL,
    energy_kwh    DOUBLE PRECISION NOT NULL
);
SELECT create_hypertable('energy_readings', 'event_time',
                         chunk_time_interval => INTERVAL '1 day');

-- --- 3. Meter metadata (reference table) --------------------------------
DROP TABLE IF EXISTS meters CASCADE;
CREATE TABLE meters (
    meter_id       BIGINT           PRIMARY KEY,
    region         TEXT             NOT NULL,
    customer_type  TEXT             NOT NULL,
    base_power_kw  DOUBLE PRECISION NOT NULL,
    power_factor   DOUBLE PRECISION NOT NULL
);

-- --- Verification -------------------------------------------------------
\echo ''
\echo '--- Table column types ---'
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name IN ('energy_live','energy_readings','meters')
ORDER BY table_name, ordinal_position;

\echo ''
\echo '--- Hypertable chunk interval ---'
SELECT hypertable_name,
       (SELECT (ds.interval_length / 1e6)::bigint AS seconds
        FROM _timescaledb_catalog.dimension d
        JOIN _timescaledb_catalog.hypertable h ON h.id = d.hypertable_id
        JOIN _timescaledb_catalog.dimension_slice ds2 ON false
        WHERE h.table_name = 'energy_readings' LIMIT 1) AS placeholder
FROM timescaledb_information.hypertables
WHERE hypertable_name='energy_readings';

SELECT hypertable_name,
       column_name,
       time_interval
FROM timescaledb_information.dimensions
WHERE hypertable_name='energy_readings';
