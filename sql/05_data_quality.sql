-- Section 2.2 - data quality checks on energy_readings (before cleaning)
SET TIME ZONE 'Africa/Kigali';

-- planned, emitted
SELECT 10752000 AS planned_readings,
       (SELECT COUNT(*) FROM energy_readings) AS emitted_readings;

-- unique pairs = distinct (meter_id, event_time)
CREATE TEMP TABLE t_pairs AS
SELECT meter_id, event_time, COUNT(*) AS k
FROM energy_readings
GROUP BY meter_id, event_time;

SELECT COUNT(*) AS unique_readings FROM t_pairs;

-- duplicates = extra copies beyond one per pair
SELECT COALESCE(SUM(k - 1), 0) AS duplicate_readings FROM t_pairs;

-- delayed = pairs whose first arrival is > 15 min after event_time
SELECT COUNT(*) AS delayed_unique_readings
FROM (SELECT meter_id, event_time, MIN(received_time) AS first_arr
      FROM energy_readings GROUP BY 1, 2) t
WHERE first_arr > event_time + INTERVAL '15 minutes';

-- missing = planned - unique
SELECT 10752000 - (SELECT COUNT(*) FROM t_pairs) AS missing_readings;

-- percentages
SELECT ROUND(100.0 * (10752000 - (SELECT COUNT(*) FROM t_pairs)) / 10752000, 4) AS missing_pct,
       ROUND(100.0 * (SELECT COALESCE(SUM(k-1),0) FROM t_pairs)
                   / (SELECT COUNT(*)       FROM t_pairs), 4) AS duplicate_pct,
       ROUND(100.0 * (SELECT COUNT(*) FROM t_pairs) / 10752000, 4) AS completeness_pct;

-- top 5 meters by missing readings
SELECT m.meter_id, m.region, m.customer_type,
       (28 * 96) - COUNT(DISTINCT e.event_time) AS missing
FROM meters m
LEFT JOIN energy_readings e USING (meter_id)
GROUP BY m.meter_id, m.region, m.customer_type
ORDER BY missing DESC, m.meter_id LIMIT 5;
