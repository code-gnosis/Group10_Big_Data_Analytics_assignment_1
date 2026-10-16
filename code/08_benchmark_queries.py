# Section 3.2 - run Q1..Q5 on three hypertables, 1 warm-up + 5 measured runs
import time
import psycopg2

TABLES = ["energy_readings", "energy_readings_3h", "energy_readings_week"]
RUNS = 5

QUERIES = {
    "Q1": """SELECT date_trunc('hour', event_time) AS h, AVG(power_kw)
             FROM {t}
             WHERE event_time >= '2026-09-21 00:00+02'
               AND event_time <  '2026-09-22 00:00+02'
             GROUP BY h ORDER BY h""",

    "Q2": """SELECT event_time, SUM(power_kw)
             FROM {t}
             WHERE event_time >= '2026-09-22 00:00+02'
               AND event_time <  '2026-09-29 00:00+02'
             GROUP BY event_time
             ORDER BY SUM(power_kw) DESC, event_time ASC
             FETCH FIRST 10 ROWS WITH TIES""",

    "Q3": """SELECT meter_id, SUM(energy_kwh)
             FROM {t}
             GROUP BY meter_id ORDER BY meter_id""",

    "Q4": """SELECT SUM(energy_kwh), AVG(power_kw), MAX(power_kw)
             FROM {t}
             WHERE meter_id = 1000000000
               AND event_time >= '2026-09-22 00:00+02'
               AND event_time <  '2026-09-29 00:00+02'""",

    "Q5": """SELECT COUNT(*), SUM(energy_kwh), AVG(power_kw),
                    MIN(power_kw), MAX(power_kw)
             FROM {t}""",
}


def run_once(cur, sql):
    t = time.time()
    cur.execute(sql)
    cur.fetchall()
    return (time.time() - t) * 1000.0


conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
cur = conn.cursor()

results = {}
session_start = time.time()

for q_name in QUERIES:
    for tbl in TABLES:
        sql = QUERIES[q_name].format(t=tbl)
        # warm up (not measured)
        cur.execute(sql); cur.fetchall()
        # 5 measured runs
        times = []
        for i in range(RUNS):
            times.append(run_once(cur, sql))
        results[(q_name, tbl)] = times
        print(f"{q_name} on {tbl}  times = {[round(x,2) for x in times]}")

session_sec = time.time() - session_start
print()
print("session seconds =", round(session_sec, 1))
print()

# summary
print("summary (median / min / max ms, warm cache):")
print(f"{'query':<4} {'table':<22} {'median':>10} {'min':>10} {'max':>10}")
for q in QUERIES:
    for tbl in TABLES:
        times = results[(q, tbl)]
        times_sorted = sorted(times)
        median = times_sorted[len(times) // 2]
        print(f"{q:<4} {tbl:<22} {median:>10.2f} {min(times):>10.2f} {max(times):>10.2f}")

cur.close()
conn.close()
