# Section 1.2 (4) - load 4000 meters into the meters table
import psycopg2
import smart_meter_simulator

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
cur = conn.cursor()

cur.execute("TRUNCATE meters")

meters = smart_meter_simulator.meter_metadata()
print("got", len(meters), "meters from generator")

for m in meters:
    cur.execute(
        "INSERT INTO meters (meter_id, region, customer_type, base_power_kw, power_factor) "
        "VALUES (%s, %s, %s, %s, %s)",
        (m["meter_id"], m["region"], m["customer_type"],
         m["base_power_kw"], m["power_factor"])
    )

conn.commit()

cur.execute("SELECT COUNT(*) FROM meters")
print("rows in meters =", cur.fetchone()[0])

cur.execute("SELECT region, COUNT(*) FROM meters GROUP BY region ORDER BY region")
for row in cur.fetchall():
    print(" ", row[0], row[1])

cur.close()
conn.close()
