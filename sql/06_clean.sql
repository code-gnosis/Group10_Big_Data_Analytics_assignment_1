-- Section 2.3 - remove exact duplicates (all 8 columns identical)
SET TIME ZONE 'Africa/Kigali';

SELECT COUNT(*) AS rows_before, SUM(energy_kwh) AS sum_before
FROM energy_readings;

-- delete duplicates keeping the row with the smallest ctid per group
DELETE FROM energy_readings e
WHERE EXISTS (
  SELECT 1 FROM energy_readings k
  WHERE k.meter_id = e.meter_id
    AND k.event_time = e.event_time
    AND k.received_time = e.received_time
    AND k.power_kw = e.power_kw
    AND k.voltage_v = e.voltage_v
    AND k.current_a = e.current_a
    AND k.frequency_hz = e.frequency_hz
    AND k.energy_kwh = e.energy_kwh
    AND k.ctid > e.ctid
);

SELECT COUNT(*) AS rows_after, SUM(energy_kwh) AS sum_after
FROM energy_readings;

-- should match expected unique_readings = 10,643,735
SELECT (COUNT(*) = 10643735) AS matches_expected FROM energy_readings;

-- any pair duplicates left? expect 0
SELECT COUNT(*) AS duplicate_pairs_left
FROM (SELECT meter_id, event_time FROM energy_readings
      GROUP BY 1, 2 HAVING COUNT(*) > 1) t;

ANALYZE energy_readings;
