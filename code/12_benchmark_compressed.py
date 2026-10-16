# Section 4.3 - run Q1..Q5 on the two compressed tables, compare to baseline
import time
import psycopg2

TABLES = ["energy_readings", "energy_time_compressed", "energy_meter_compressed"]
RUNS = 5

QUERIES = {
    "Q1": """SELECT date_trunc('hour', event_time), AVG(power_kw) FROM {t}
             WHERE event_time >= '2026-09-21 00:00+02'
               AND event_time <  '2026-09-22 00:00+02'
             GROUP BY 1 ORDER BY 1""",
    "Q2": """SELECT event_time, SUM(power_kw) FROM {t}
             WHERE event_time >= '2026-09-22 00:00+02'
               AND event_time <  '2026-09-29 00:00+02'
             GROUP BY event_time ORDER BY SUM(power_kw) DESC, event_time ASC
             FETCH FIRST 10 ROWS WITH TIES""",
    "Q3": """SELECT meter_id, SUM(energy_kwh) FROM {t}
             GROUP BY meter_id ORDER BY meter_id""",
    "Q4": """SELECT SUM(energy_kwh), AVG(power_kw), MAX(power_kw) FROM {t}
             WHERE meter_id = 1000000000
               AND event_time >= '2026-09-22 00:00+02'
               AND event_time <  '2026-09-29 00:00+02'""",
    "Q5": """SELECT COUNT(*), SUM(energy_kwh), AVG(power_kw),
                    MIN(power_kw), MAX(power_kw) FROM {t}""",
}

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
cur = conn.cursor()

results = {}
for q in QUERIES:
    for tbl in TABLES:
        sql = QUERIES[q].format(t=tbl)
        cur.execute(sql); cur.fetchall()      # warm-up
        times = []
        for i in range(RUNS):
            t = time.time()
            cur.execute(sql); cur.fetchall()
            times.append((time.time() - t) * 1000)
        median = sorted(times)[len(times)//2]
        results[(q, tbl)] = median
        print(f"{q} / {tbl:<24} median = {median:.2f} ms")

print()
print(f"{'query':<4} {'baseline':>10} {'time_c':>10} {'meter_c':>10} "
      f"{'%impr_t':>8} {'%impr_m':>8}")
for q in QUERIES:
    b = results[(q, "energy_readings")]
    t = results[(q, "energy_time_compressed")]
    m = results[(q, "energy_meter_compressed")]
    imp_t = 100.0 * (b - t) / b
    imp_m = 100.0 * (b - m) / b
    print(f"{q:<4} {b:>10.2f} {t:>10.2f} {m:>10.2f} {imp_t:>8.1f} {imp_m:>8.1f}")

cur.close()
conn.close()
