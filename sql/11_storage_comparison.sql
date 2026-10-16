-- Section 4.2 — Storage sizes for baseline + two compressed tables.
SET TIME ZONE 'Africa/Kigali';

\echo '--- Row count & data checks (must still match baseline) ---'
SELECT 'energy_readings'          AS tbl, COUNT(*) AS rows,
       ROUND(SUM(energy_kwh)::numeric,3) AS sum_e,
       ROUND(SUM(power_kw)::numeric,3)   AS sum_p
FROM energy_readings
UNION ALL
SELECT 'energy_time_compressed',  COUNT(*),
       ROUND(SUM(energy_kwh)::numeric,3), ROUND(SUM(power_kw)::numeric,3)
FROM energy_time_compressed
UNION ALL
SELECT 'energy_meter_compressed', COUNT(*),
       ROUND(SUM(energy_kwh)::numeric,3), ROUND(SUM(power_kw)::numeric,3)
FROM energy_meter_compressed;

\echo ''
\echo '--- Chunk compression status ---'
SELECT hypertable_name,
       COUNT(*)                              AS total_chunks,
       COUNT(*) FILTER (WHERE is_compressed) AS compressed_chunks
FROM timescaledb_information.chunks
WHERE hypertable_name IN ('energy_readings','energy_time_compressed','energy_meter_compressed')
GROUP BY hypertable_name
ORDER BY hypertable_name;

\echo ''
\echo '--- Storage sizes (bytes) ---'
SELECT hypertable_name,
       pg_size_pretty(SUM(total_bytes))         AS total,
       pg_size_pretty(SUM(table_bytes))         AS table_data,
       pg_size_pretty(SUM(index_bytes))         AS index_bytes,
       pg_size_pretty(SUM(compressed_total_bytes)) AS compressed_total,
       SUM(total_bytes)                         AS total_raw
FROM (
  SELECT 'energy_readings' AS hypertable_name, * FROM chunks_detailed_size('energy_readings')
  UNION ALL
  SELECT 'energy_time_compressed',  * FROM chunks_detailed_size('energy_time_compressed')
  UNION ALL
  SELECT 'energy_meter_compressed', * FROM chunks_detailed_size('energy_meter_compressed')
) s
GROUP BY hypertable_name
ORDER BY hypertable_name;

\echo ''
\echo '--- Compression ratios vs baseline (energy_readings 1-day) ---'
WITH b AS (SELECT SUM(total_bytes) AS n FROM chunks_detailed_size('energy_readings')),
     t AS (SELECT SUM(total_bytes) AS n FROM chunks_detailed_size('energy_time_compressed')),
     m AS (SELECT SUM(total_bytes) AS n FROM chunks_detailed_size('energy_meter_compressed'))
SELECT
    pg_size_pretty((SELECT n FROM b)) AS baseline,
    pg_size_pretty((SELECT n FROM t)) AS time_only,
    pg_size_pretty((SELECT n FROM m)) AS meter_seg,
    ROUND(((SELECT n FROM b))::numeric / (SELECT n FROM t), 2) AS ratio_time,
    ROUND(((SELECT n FROM b))::numeric / (SELECT n FROM m), 2) AS ratio_meter,
    ROUND(100.0*(1 - (SELECT n FROM t)::numeric/(SELECT n FROM b)),2) AS saved_pct_time,
    ROUND(100.0*(1 - (SELECT n FROM m)::numeric/(SELECT n FROM b)),2) AS saved_pct_meter;
