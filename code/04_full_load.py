# Section 2.1 - generate CSV from the generator then COPY into energy_readings
import csv
import time
import psycopg2
import smart_meter_simulator

CSV_FILE = "../data/energy_readings.csv"

info = smart_meter_simulator.dataset_info()
expected = info["expected_counts"]["emitted_readings"]
print("expected emitted_readings =", expected)

# Phase 1: write CSV
print("writing CSV...")
start_gen = time.time()
count = 0
f = open(CSV_FILE, "w", newline="")
w = csv.writer(f)
w.writerow(["meter_id", "event_time", "received_time",
            "power_kw", "voltage_v", "current_a",
            "frequency_hz", "energy_kwh"])
for r in smart_meter_simulator.iter_readings():
    w.writerow([r["meter_id"], r["event_time"], r["received_time"],
                r["power_kw"], r["voltage_v"], r["current_a"],
                r["frequency_hz"], r["energy_kwh"]])
    count += 1
    if count % 500000 == 0:
        print(" ", count, "rows,", round(time.time() - start_gen, 1), "s")
f.close()
gen_sec = time.time() - start_gen
print("CSV done:", count, "rows in", round(gen_sec, 1), "s")

# Phase 2: COPY into energy_readings
print("loading into database...")
conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
cur = conn.cursor()
cur.execute("TRUNCATE energy_readings")
conn.commit()

start_load = time.time()
f = open(CSV_FILE, "r")
cur.copy_expert(
    "COPY energy_readings (meter_id, event_time, received_time, "
    "power_kw, voltage_v, current_a, frequency_hz, energy_kwh) "
    "FROM STDIN WITH (FORMAT csv, HEADER true)", f
)
conn.commit()
f.close()
load_sec = time.time() - start_load

# Phase 3: verify
cur.execute("SELECT COUNT(*) FROM energy_readings")
rows = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT meter_id), MIN(event_time), MAX(event_time) "
            "FROM energy_readings")
meters, earliest, latest = cur.fetchone()

cur.execute("SELECT pg_size_pretty(hypertable_size('energy_readings'))")
size = cur.fetchone()[0]

print()
print("expected      =", expected)
print("CSV rows      =", count)
print("DB rows       =", rows)
print("CSV gen time  =", round(gen_sec, 1), "s")
print("COPY load time=", round(load_sec, 1), "s")
print("meters        =", meters)
print("earliest      =", earliest)
print("latest        =", latest)
print("hypertable    =", size)

cur.close()
conn.close()
