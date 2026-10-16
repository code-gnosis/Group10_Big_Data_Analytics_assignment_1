# Section 5 - utility data analysis
import json
import psycopg2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import smart_meter_simulator

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
cur = conn.cursor()
cur.execute("SET TIME ZONE 'Africa/Kigali'")

# 5.1 daily totals
print("=== 5.1 Daily network energy ===")
cur.execute("""
    SELECT date_trunc('day', event_time)::date, SUM(energy_kwh)
    FROM energy_readings
    GROUP BY 1 ORDER BY 1
""")
daily = cur.fetchall()
for day, kwh in daily:
    print(" ", day, round(float(kwh), 2))

# bar plot
days   = [str(x[0]) for x in daily]
values = [float(x[1]) for x in daily]
plt.figure(figsize=(10, 4))
plt.bar(days, values)
plt.title("Daily network energy (kWh)")
plt.xticks(rotation=70)
plt.tight_layout()
plt.savefig("../outputs/fig_51_daily_energy.png", dpi=120)
plt.close()

# 5.1 weekly
print()
print("=== 5.1 Weekly totals (7-day windows) ===")
for start_day in ["2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22"]:
    cur.execute("""
        SELECT SUM(energy_kwh) FROM energy_readings
        WHERE event_time >= %s::timestamptz
          AND event_time <  (%s::date + 7)::timestamptz
    """, (start_day, start_day))
    print(" ", start_day, "->", round(float(cur.fetchone()[0]), 2))

# 5.1 top 3 peak
print()
print("=== 5.1 Top 3 peak 15-min intervals ===")
cur.execute("""
    SELECT event_time, SUM(power_kw)
    FROM energy_readings
    GROUP BY event_time
    ORDER BY SUM(power_kw) DESC LIMIT 3
""")
for et, kw in cur.fetchall():
    print(" ", et, round(float(kw), 2), "kW")

# 5.2 by region
print()
print("=== 5.2 Energy by region ===")
cur.execute("""
    SELECT m.region, COUNT(DISTINCT m.meter_id),
           SUM(e.energy_kwh),
           SUM(e.energy_kwh) / COUNT(DISTINCT m.meter_id)
    FROM energy_readings e JOIN meters m USING (meter_id)
    GROUP BY m.region ORDER BY m.region
""")
for row in cur.fetchall():
    print(" ", row[0], "meters=", row[1],
          "total=", round(float(row[2]), 2),
          "per_meter=", round(float(row[3]), 2))

# 5.2 by customer type
print()
print("=== 5.2 Energy by customer type ===")
cur.execute("""
    SELECT m.customer_type, COUNT(DISTINCT m.meter_id),
           SUM(e.energy_kwh),
           SUM(e.energy_kwh) / COUNT(DISTINCT m.meter_id)
    FROM energy_readings e JOIN meters m USING (meter_id)
    GROUP BY m.customer_type ORDER BY m.customer_type
""")
for row in cur.fetchall():
    print(" ", row[0], "meters=", row[1],
          "total=", round(float(row[2]), 2),
          "per_meter=", round(float(row[3]), 2))

# 5.3 completeness - network
print()
print("=== 5.3 Completeness ===")
cur.execute("""
    SELECT COUNT(*) FROM (
        SELECT DISTINCT meter_id, event_time FROM energy_readings
    ) t
""")
observed = cur.fetchone()[0]
planned = 4000 * 28 * 96
print("  network: planned=", planned, "observed=", observed,
      "completeness=", round(100.0 * observed / planned, 4), "%")

# 5.3 per region
cur.execute("""
    SELECT m.region, COUNT(DISTINCT (e.meter_id, e.event_time))
    FROM energy_readings e JOIN meters m USING (meter_id)
    GROUP BY m.region ORDER BY m.region
""")
for region, obs in cur.fetchall():
    planned_r = 400 * 28 * 96
    print("  ", region, "planned=", planned_r, "observed=", obs,
          "completeness=", round(100.0 * obs / planned_r, 4), "%")

# 5.3 21 Sep early vs full
print()
print("=== 5.3 21 Sep delayed arrivals ===")
cur.execute("""
    SELECT SUM(energy_kwh) FROM energy_readings
    WHERE event_time >= '2026-09-21 00:00+02'
      AND event_time <  '2026-09-22 00:00+02'
      AND received_time <= '2026-09-22 00:00+02'
""")
early = float(cur.fetchone()[0])
cur.execute("""
    SELECT SUM(energy_kwh) FROM energy_readings
    WHERE event_time >= '2026-09-21 00:00+02'
      AND event_time <  '2026-09-22 00:00+02'
""")
full = float(cur.fetchone()[0])
diff = full - early
pct = 100.0 * diff / full
print("  early arrivals  =", round(early, 2), "kWh")
print("  all arrivals    =", round(full,  2), "kWh")
print("  difference      =", round(diff,  2), "kWh (", round(pct, 4), "% of full)")

# 5.4 anomaly detection using MAD
print()
print("=== 5.4 Anomaly detection ===")

# compute median and MAD per meter
cur.execute("DROP TABLE IF EXISTS tmp_stats")
cur.execute("""
    CREATE TEMP TABLE tmp_stats AS
    SELECT meter_id,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY power_kw) AS med
    FROM energy_readings GROUP BY meter_id
""")
cur.execute("CREATE INDEX ON tmp_stats (meter_id)")

cur.execute("""
    CREATE TEMP TABLE tmp_mad AS
    SELECT e.meter_id, s.med,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY abs(e.power_kw - s.med)) AS mad
    FROM energy_readings e JOIN tmp_stats s USING (meter_id)
    GROUP BY e.meter_id, s.med
""")
cur.execute("CREATE INDEX ON tmp_mad (meter_id)")

# flag readings more than 3 * 1.4826 * MAD from median
cur.execute("""
    CREATE TEMP TABLE tmp_flagged AS
    SELECT e.meter_id, e.event_time
    FROM energy_readings e JOIN tmp_mad s USING (meter_id)
    WHERE s.mad > 0
      AND abs(e.power_kw - s.med) > 3 * s.mad * 1.4826
""")
cur.execute("SELECT COUNT(*) FROM tmp_flagged")
flags = cur.fetchone()[0]
print("  flags =", flags)

# compare with injected events
events = smart_meter_simulator.anomaly_events()
print("  injected events =", len(events))

cur.execute("CREATE TEMP TABLE tmp_events "
            "(meter_id BIGINT, start_time TIMESTAMPTZ, end_time TIMESTAMPTZ)")
for e in events:
    cur.execute("INSERT INTO tmp_events VALUES (%s, %s, %s)",
                (e["meter_id"], e["start_time"], e["end_time"]))

cur.execute("""
    SELECT COUNT(*) FROM tmp_events a
    WHERE EXISTS (
        SELECT 1 FROM tmp_flagged f
        WHERE f.meter_id = a.meter_id
          AND f.event_time >= a.start_time
          AND f.event_time <  a.end_time)
""")
detected = cur.fetchone()[0]
missed = len(events) - detected
print("  detected =", detected, " missed =", missed)

# false flags = flagged readings outside any injected interval
cur.execute("""
    SELECT COUNT(*) FROM tmp_flagged f
    WHERE NOT EXISTS (
        SELECT 1 FROM tmp_events a
        WHERE a.meter_id = f.meter_id
          AND f.event_time >= a.start_time
          AND f.event_time <  a.end_time)
""")
false_flags = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM energy_readings e
    WHERE NOT EXISTS (
        SELECT 1 FROM tmp_events a
        WHERE a.meter_id = e.meter_id
          AND e.event_time >= a.start_time
          AND e.event_time <  a.end_time)
""")
outside = cur.fetchone()[0]
print("  false flags =", false_flags, "(", round(100.0 * false_flags / outside, 4), "% of outside)")

cur.execute("""
    SELECT COUNT(DISTINCT meter_id) FROM tmp_flagged f
    WHERE NOT EXISTS (
        SELECT 1 FROM tmp_events a
        WHERE a.meter_id = f.meter_id
          AND f.event_time >= a.start_time
          AND f.event_time <  a.end_time)
""")
meters_fp = cur.fetchone()[0]
print("  meters with >= 1 false flag =", meters_fp,
      "(", round(100.0 * meters_fp / 4000, 2), "% of 4000)")

cur.close()
conn.close()
