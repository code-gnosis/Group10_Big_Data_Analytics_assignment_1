-- Section 6.1 — Three continuous aggregate views over energy_readings.
SET TIME ZONE 'Africa/Kigali';

DROP MATERIALIZED VIEW IF EXISTS cagg_15m_region CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cagg_hour_region CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cagg_day_meter   CASCADE;

CREATE MATERIALIZED VIEW cagg_15m_region
WITH (timescaledb.continuous, timescaledb.materialized_only = TRUE) AS
SELECT time_bucket('15 minutes', e.event_time) AS bucket,
       m.region,
       SUM(e.energy_kwh) AS energy_kwh,
       SUM(e.power_kw)   AS power_kw,
       COUNT(*)          AS reading_count
FROM energy_readings e
JOIN meters m USING (meter_id)
GROUP BY 1, 2
WITH NO DATA;

CREATE MATERIALIZED VIEW cagg_hour_region
WITH (timescaledb.continuous, timescaledb.materialized_only = TRUE) AS
SELECT time_bucket('1 hour', e.event_time) AS bucket,
       m.region,
       SUM(e.energy_kwh) AS energy_kwh,
       SUM(e.power_kw)   AS power_kw,
       COUNT(*)          AS reading_count
FROM energy_readings e
JOIN meters m USING (meter_id)
GROUP BY 1, 2
WITH NO DATA;

CREATE MATERIALIZED VIEW cagg_day_meter
WITH (timescaledb.continuous, timescaledb.materialized_only = TRUE) AS
SELECT time_bucket('1 day', event_time) AS bucket,
       meter_id,
       SUM(energy_kwh) AS energy_kwh,
       SUM(power_kw)   AS power_kw,
       COUNT(*)        AS reading_count
FROM energy_readings
GROUP BY 1, 2
WITH NO DATA;

\echo '--- Views created, measuring initial refresh ---'
\timing on
CALL refresh_continuous_aggregate('cagg_15m_region',  NULL, NULL);
CALL refresh_continuous_aggregate('cagg_hour_region', NULL, NULL);
CALL refresh_continuous_aggregate('cagg_day_meter',   NULL, NULL);
\timing off

\echo ''
\echo '--- Sample rows from each ---'
SELECT bucket, region, energy_kwh, reading_count FROM cagg_15m_region  ORDER BY bucket LIMIT 3;
SELECT bucket, region, energy_kwh, reading_count FROM cagg_hour_region ORDER BY bucket LIMIT 3;
SELECT bucket, meter_id, energy_kwh, reading_count FROM cagg_day_meter ORDER BY bucket, meter_id LIMIT 3;

\echo ''
\echo '--- Materialized sizes ---'
SELECT view_name,
       pg_size_pretty(pg_total_relation_size(materialization_hypertable_schema||'.'||materialization_hypertable_name)) AS size
FROM timescaledb_information.continuous_aggregates
WHERE view_schema = 'public'
ORDER BY view_name;

\echo ''
\echo '--- Add refresh policies (3-day lookback, 1h end offset, 15-min schedule) ---'
SELECT add_continuous_aggregate_policy('cagg_15m_region',
       start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
       schedule_interval => INTERVAL '15 minutes');
SELECT add_continuous_aggregate_policy('cagg_hour_region',
       start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
       schedule_interval => INTERVAL '15 minutes');
SELECT add_continuous_aggregate_policy('cagg_day_meter',
       start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
       schedule_interval => INTERVAL '15 minutes');

\echo ''
\echo '--- Background jobs ---'
SELECT job_id, application_name, schedule_interval, scheduled
FROM timescaledb_information.jobs
WHERE application_name LIKE 'Refresh%'
ORDER BY job_id;
