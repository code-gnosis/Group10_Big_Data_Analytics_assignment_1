-- Section 3.1 — Three hypertables with matching indexes.
SET TIME ZONE 'Africa/Kigali';

-- ---- 1. Add matching (meter_id, event_time) index to the existing 1-day table.
CREATE INDEX IF NOT EXISTS energy_readings_meter_time_idx
    ON energy_readings (meter_id, event_time);

-- ---- 2. 3-hour hypertable
DROP TABLE IF EXISTS energy_readings_3h CASCADE;
CREATE TABLE energy_readings_3h (LIKE energy_readings INCLUDING DEFAULTS);
SELECT create_hypertable('energy_readings_3h', 'event_time',
                         chunk_time_interval => INTERVAL '3 hours');
INSERT INTO energy_readings_3h SELECT * FROM energy_readings;
CREATE INDEX energy_readings_3h_event_time_idx   ON energy_readings_3h (event_time DESC);
CREATE INDEX energy_readings_3h_meter_time_idx   ON energy_readings_3h (meter_id, event_time);

-- ---- 3. 1-week hypertable
DROP TABLE IF EXISTS energy_readings_week CASCADE;
CREATE TABLE energy_readings_week (LIKE energy_readings INCLUDING DEFAULTS);
SELECT create_hypertable('energy_readings_week', 'event_time',
                         chunk_time_interval => INTERVAL '1 week');
INSERT INTO energy_readings_week SELECT * FROM energy_readings;
CREATE INDEX energy_readings_week_event_time_idx ON energy_readings_week (event_time DESC);
CREATE INDEX energy_readings_week_meter_time_idx ON energy_readings_week (meter_id, event_time);

ANALYZE energy_readings;
ANALYZE energy_readings_3h;
ANALYZE energy_readings_week;

-- ---- 4. Matching data checks
\echo ''
\echo '--- Chunk counts and intervals ---'
SELECT hypertable_name, time_interval,
       (SELECT COUNT(*) FROM show_chunks(hypertable_name::regclass)) AS chunks
FROM timescaledb_information.dimensions
WHERE hypertable_name LIKE 'energy_readings%'
ORDER BY hypertable_name;

\echo ''
\echo '--- Row-count / meter-count / date / sum checks on all 3 tables ---'
SELECT 'energy_readings'      AS tbl,
       COUNT(*)               AS rows,
       COUNT(DISTINCT meter_id) AS meters,
       MIN(event_time)        AS earliest,
       MAX(event_time)        AS latest,
       ROUND(SUM(power_kw)::numeric, 3)   AS sum_power_kw,
       ROUND(SUM(energy_kwh)::numeric, 3) AS sum_energy_kwh
FROM energy_readings
UNION ALL
SELECT 'energy_readings_3h', COUNT(*), COUNT(DISTINCT meter_id),
       MIN(event_time), MAX(event_time),
       ROUND(SUM(power_kw)::numeric, 3), ROUND(SUM(energy_kwh)::numeric, 3)
FROM energy_readings_3h
UNION ALL
SELECT 'energy_readings_week', COUNT(*), COUNT(DISTINCT meter_id),
       MIN(event_time), MAX(event_time),
       ROUND(SUM(power_kw)::numeric, 3), ROUND(SUM(energy_kwh)::numeric, 3)
FROM energy_readings_week
ORDER BY tbl;

\echo ''
\echo '--- Indexes on each table ---'
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname='public' AND tablename LIKE 'energy_readings%'
ORDER BY tablename, indexname;
