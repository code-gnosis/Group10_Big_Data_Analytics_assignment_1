-- Section 3.2 (5) — EXPLAIN (ANALYZE, BUFFERS) one query per hypertable.
-- Using Q1 (hourly avg on 21 Sept) since it best demonstrates chunk pruning.

\echo '═══ Q1 on energy_readings (1-day chunks) ═══'
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
SELECT date_trunc('hour', event_time) AS h, AVG(power_kw) AS avg_kw
FROM energy_readings
WHERE event_time >= '2026-09-21 00:00+02' AND event_time < '2026-09-22 00:00+02'
GROUP BY h ORDER BY h;

\echo ''
\echo '═══ Q1 on energy_readings_3h (3-hour chunks) ═══'
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
SELECT date_trunc('hour', event_time) AS h, AVG(power_kw) AS avg_kw
FROM energy_readings_3h
WHERE event_time >= '2026-09-21 00:00+02' AND event_time < '2026-09-22 00:00+02'
GROUP BY h ORDER BY h;

\echo ''
\echo '═══ Q1 on energy_readings_week (1-week chunks) ═══'
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
SELECT date_trunc('hour', event_time) AS h, AVG(power_kw) AS avg_kw
FROM energy_readings_week
WHERE event_time >= '2026-09-21 00:00+02' AND event_time < '2026-09-22 00:00+02'
GROUP BY h ORDER BY h;
