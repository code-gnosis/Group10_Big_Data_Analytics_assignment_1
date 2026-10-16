# Section 4.1 (5) - compress each chunk whose range_end is older than cutoff
import time
import psycopg2
from datetime import datetime, timedelta, timezone

CAT = timezone(timedelta(hours=2))
cutoff = datetime.now(CAT) - timedelta(hours=48)
print("cutoff =", cutoff)

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
conn.autocommit = True
cur = conn.cursor()

for table in ["energy_time_compressed", "energy_meter_compressed"]:
    cur.execute(
        "SELECT chunk_schema || '.' || chunk_name, range_end "
        "FROM timescaledb_information.chunks "
        "WHERE hypertable_name = %s ORDER BY range_end", (table,)
    )
    chunks = cur.fetchall()
    print()
    print(table, "- found", len(chunks), "chunks")

    total = 0.0
    count = 0
    for chunk, range_end in chunks:
        if range_end > cutoff:
            print(" skip", chunk, "(too recent)")
            continue
        t = time.time()
        cur.execute("SELECT compress_chunk(%s::regclass, if_not_compressed => true)",
                    (chunk,))
        dt = (time.time() - t) * 1000
        total += dt
        count += 1
        print(f"  compressed {chunk}  {dt:.0f} ms")

    print(f" {table}: {count} chunks compressed, total {total/1000:.2f} s, "
          f"avg {total/count:.1f} ms/chunk")

cur.close()
conn.close()
