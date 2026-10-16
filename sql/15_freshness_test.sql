-- Section 6.2 — Freshness and delayed-arrival test.
SET TIME ZONE 'Africa/Kigali';
DROP MATERIALIZED VIEW IF EXISTS test_hourly_cagg CASCADE;
DROP TABLE IF EXISTS test_hypertable CASCADE;

CREATE TABLE test_hypertable (
    event_time TIMESTAMPTZ      NOT NULL,
    energy_kwh DOUBLE PRECISION NOT NULL
);
SELECT create_hypertable('test_hypertable', 'event_time',
                         chunk_time_interval => INTERVAL '1 day');

CREATE MATERIALIZED VIEW test_hourly_cagg
WITH (timescaledb.continuous, timescaledb.materialized_only = TRUE) AS
SELECT time_bucket('1 hour', event_time) AS bucket,
       SUM(energy_kwh) AS energy_kwh,
       COUNT(*)        AS rows
FROM test_hypertable GROUP BY 1
WITH NO DATA;

\echo '--- Record timestamps ---'
WITH t AS (
  SELECT now() AS test_time,
         date_trunc('hour', now()) - INTERVAL '1 hour' AS H,
         date_trunc('hour', now()) - INTERVAL '1 hour' - INTERVAL '48 hours' AS H_minus_48
)
SELECT test_time, H, H_minus_48 FROM t;

-- Save the two timestamps as session variables via WITH ... INSERT so we can reuse them
-- Using a conventional approach: compute inline each time.

\echo ''
\echo '--- Stage 1: insert 1 kWh into older hour, manual refresh ONLY that hour ---'
INSERT INTO test_hypertable (event_time, energy_kwh)
VALUES (date_trunc('hour', now()) - INTERVAL '49 hours' + INTERVAL '10 minutes', 1.0);
CALL refresh_continuous_aggregate('test_hourly_cagg',
    date_trunc('hour', now()) - INTERVAL '49 hours',
    date_trunc('hour', now()) - INTERVAL '48 hours');

\echo 'Older hour aggregate after Stage 1 (expect 1 kWh, 1 row):'
SELECT bucket, energy_kwh, rows FROM test_hourly_cagg
WHERE bucket = date_trunc('hour', now()) - INTERVAL '49 hours';
\echo 'Hour H aggregate after Stage 1 (expect no row):'
SELECT bucket, energy_kwh, rows FROM test_hourly_cagg
WHERE bucket = date_trunc('hour', now()) - INTERVAL '1 hour';

\echo ''
\echo '--- Stage 2: insert +0.5 kWh older, +2 kWh H ---'
INSERT INTO test_hypertable VALUES
  (date_trunc('hour', now()) - INTERVAL '49 hours' + INTERVAL '25 minutes', 0.5),
  (date_trunc('hour', now()) - INTERVAL '1 hour'   + INTERVAL '10 minutes', 2.0);

\echo 'Raw table after inserts:'
SELECT bucket, SUM(energy_kwh) AS raw_e, COUNT(*) AS raw_rows FROM (
  SELECT time_bucket('1 hour', event_time) AS bucket, energy_kwh FROM test_hypertable
) t GROUP BY bucket ORDER BY bucket;

\echo 'Aggregate (real-time OFF, no refresh yet) — expect 1 kWh older + no H row:'
SELECT bucket, energy_kwh, rows FROM test_hourly_cagg ORDER BY bucket;

\echo ''
\echo '--- Stage 3: enable real-time aggregation ---'
ALTER MATERIALIZED VIEW test_hourly_cagg SET (timescaledb.materialized_only = FALSE);

\echo 'Aggregate (real-time ON, no refresh yet) — expect 1 kWh older, 2 kWh H:'
SELECT bucket, energy_kwh, rows FROM test_hourly_cagg ORDER BY bucket;

\echo ''
\echo '--- Stage 4: manual refresh both complete hours ---'
CALL refresh_continuous_aggregate('test_hourly_cagg',
    date_trunc('hour', now()) - INTERVAL '49 hours',
    date_trunc('hour', now()) - INTERVAL '48 hours');
CALL refresh_continuous_aggregate('test_hourly_cagg',
    date_trunc('hour', now()) - INTERVAL '1 hour',
    date_trunc('hour', now()));

\echo 'Final aggregate (expect 1.5 kWh/2 rows older; 2 kWh/1 row H):'
SELECT bucket, energy_kwh, rows FROM test_hourly_cagg ORDER BY bucket;
