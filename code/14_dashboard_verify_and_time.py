# Section 7.3 + 7.4 - verify Raw vs Aggregate match + time each panel
import json
import time
import psycopg2

TIME_FROM = "2026-09-22 00:00:00+02"
TIME_TO   = "2026-09-29 00:00:00+02"

def fix_grafana(sql):
    # replace Grafana macros with real values
    sql = sql.replace("$__timeFilter(e.event_time)",
                      f"e.event_time >= '{TIME_FROM}' AND e.event_time < '{TIME_TO}'")
    sql = sql.replace("$__timeFilter(event_time)",
                      f"event_time >= '{TIME_FROM}' AND event_time < '{TIME_TO}'")
    sql = sql.replace("$__timeFilter(bucket)",
                      f"bucket >= '{TIME_FROM}' AND bucket < '{TIME_TO}'")
    sql = sql.replace("$__timeFrom()", f"'{TIME_FROM}'")
    sql = sql.replace("$__timeTo()",   f"'{TIME_TO}'")
    return sql


def load_panels(path):
    with open(path) as f:
        d = json.load(f)
    out = []
    for p in d["panels"]:
        out.append((p["id"], p["title"], fix_grafana(p["targets"][0]["rawSql"])))
    return out


raw = load_panels("../grafana/dashboards/raw.json")
agg = load_panels("../grafana/dashboards/aggregate.json")

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
cur = conn.cursor()
cur.execute("SET TIME ZONE 'Africa/Kigali'")

# 7.3 compare row by row
print("=== 7.3 Verify matching ===")
for (rid, rt, rsql), (aid, at, asql) in zip(raw, agg):
    cur.execute(rsql); r_rows = cur.fetchall()
    cur.execute(asql); a_rows = cur.fetchall()
    max_diff = 0.0
    for ra, ag in zip(r_rows, a_rows):
        for v1, v2 in zip(ra, ag):
            try:
                d = abs(float(v1) - float(v2))
                if d > max_diff:
                    max_diff = d
            except (TypeError, ValueError):
                pass
    print(f"  panel {rid} [{rt}]  raw_rows={len(r_rows)} agg_rows={len(a_rows)} "
          f"max_abs_diff={max_diff:.6f}")

# 7.4 time each panel (1 warm-up + 10 measured runs)
print()
print("=== 7.4 Timings (warm cache) ===")
WARMUP = 1
RUNS = 10

for mode, panels in [("Raw", raw), ("Aggregate", agg)]:
    print()
    print(mode, "dashboard")
    total_times = []
    for i in range(RUNS):
        t = time.time()
        for pid, title, sql in panels:
            cur.execute(sql); cur.fetchall()
        total_times.append((time.time() - t) * 1000)
    sorted_t = sorted(total_times)
    print(f"  total refresh: median={sorted_t[RUNS//2]:.1f} min={min(total_times):.1f} "
          f"max={max(total_times):.1f} ms")

    for pid, title, sql in panels:
        for _ in range(WARMUP):
            cur.execute(sql); cur.fetchall()
        times = []
        for _ in range(RUNS):
            t = time.time()
            cur.execute(sql); cur.fetchall()
            times.append((time.time() - t) * 1000)
        s = sorted(times)
        print(f"  panel {pid}: median={s[RUNS//2]:.2f} min={min(times):.2f} max={max(times):.2f} ms "
              f"- {title}")

cur.close()
conn.close()
