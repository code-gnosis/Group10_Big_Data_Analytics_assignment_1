# Section 4.1 - build two compressed hypertables with 1-day chunks
import time
import psycopg2
from datetime import datetime, timedelta, timezone

CAT = timezone(timedelta(hours=2))

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SET TIME ZONE 'Africa/Kigali'")

# cutoff = experiment start - 48 hours (used in 4.1 point 4)
cutoff = datetime.now(CAT) - timedelta(hours=48)
print("experiment start =", datetime.now(CAT))
print("cutoff (now-48h) =", cutoff)

# drop old versions and rebuild
cur.execute("DROP TABLE IF EXISTS energy_time_compressed CASCADE")
cur.execute("DROP TABLE IF EXISTS energy_meter_compressed CASCADE")

# time-only compression
cur.execute("CREATE TABLE energy_time_compressed (LIKE energy_readings INCLUDING DEFAULTS)")
cur.execute("SELECT create_hypertable('energy_time_compressed', 'event_time', "
            "chunk_time_interval => INTERVAL '1 day')")
cur.execute("ALTER TABLE energy_time_compressed SET "
            "(timescaledb.compress, timescaledb.compress_orderby = 'event_time DESC')")
cur.execute("CREATE INDEX etc_time_idx  ON energy_time_compressed (event_time DESC)")
cur.execute("CREATE INDEX etc_meter_idx ON energy_time_compressed (meter_id, event_time)")

# meter-segmented compression
cur.execute("CREATE TABLE energy_meter_compressed (LIKE energy_readings INCLUDING DEFAULTS)")
cur.execute("SELECT create_hypertable('energy_meter_compressed', 'event_time', "
            "chunk_time_interval => INTERVAL '1 day')")
cur.execute("ALTER TABLE energy_meter_compressed SET "
            "(timescaledb.compress, timescaledb.compress_orderby = 'event_time DESC', "
            " timescaledb.compress_segmentby = 'meter_id')")
cur.execute("CREATE INDEX emc_time_idx  ON energy_meter_compressed (event_time DESC)")
cur.execute("CREATE INDEX emc_meter_idx ON energy_meter_compressed (meter_id, event_time)")

# add policies then pause them (we compress manually in 10b)
cur.execute("SELECT add_compression_policy('energy_time_compressed', INTERVAL '48 hours')")
pol1 = cur.fetchone()[0]
cur.execute("SELECT alter_job(%s, scheduled => false)", (pol1,))

cur.execute("SELECT add_compression_policy('energy_meter_compressed', INTERVAL '48 hours')")
pol2 = cur.fetchone()[0]
cur.execute("SELECT alter_job(%s, scheduled => false)", (pol2,))

print("policies created and paused:", pol1, pol2)

# copy data one day at a time
cur.execute("SELECT date_trunc('day', event_time)::date "
            "FROM energy_readings GROUP BY 1 ORDER BY 1")
days = [row[0] for row in cur.fetchall()]
print("loading", len(days), "days")

load_time_total = 0
load_meter_total = 0

for day in days:
    start = datetime(day.year, day.month, day.day, tzinfo=CAT)
    end = start + timedelta(days=1)

    t = time.time()
    cur.execute("INSERT INTO energy_time_compressed SELECT * FROM energy_readings "
                "WHERE event_time >= %s AND event_time < %s", (start, end))
    load_time_total += time.time() - t

    t = time.time()
    cur.execute("INSERT INTO energy_meter_compressed SELECT * FROM energy_readings "
                "WHERE event_time >= %s AND event_time < %s", (start, end))
    load_meter_total += time.time() - t

    print(" loaded", day)

cur.execute("ANALYZE energy_time_compressed")
cur.execute("ANALYZE energy_meter_compressed")

print()
print("time-only  load total =", round(load_time_total, 2), "s")
print("meter-seg  load total =", round(load_meter_total, 2), "s")
print("now run 10b_compress_old_chunks.py to actually compress")

cur.close()
conn.close()
