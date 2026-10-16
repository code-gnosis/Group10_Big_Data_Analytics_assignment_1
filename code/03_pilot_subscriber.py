# Section 1.3 - pilot subscriber: receive MQTT messages and insert into energy_live
import json
import psycopg2
import paho.mqtt.client as mqtt

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
conn.autocommit = True
cur = conn.cursor()

received = 0

def on_connect(client, userdata, flags, rc):
    print("connected rc =", rc)
    client.subscribe("energy/meters/#", qos=1)
    print("subscribed to energy/meters/#")

def on_message(client, userdata, msg):
    global received
    r = json.loads(msg.payload)
    cur.execute(
        "INSERT INTO energy_live (meter_id, event_time, received_time, "
        "power_kw, voltage_v, current_a, frequency_hz, energy_kwh) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (r["meter_id"], r["event_time"], r["received_time"],
         r["power_kw"], r["voltage_v"], r["current_a"],
         r["frequency_hz"], r["energy_kwh"])
    )
    received += 1
    if received % 500 == 0:
        print("received", received)

client = mqtt.Client(client_id="pilot_sub", clean_session=True)
client.on_connect = on_connect
client.on_message = on_message
client.connect("127.0.0.1", 1883, 60)

print("subscriber running, Ctrl+C to stop")
try:
    client.loop_forever()
except KeyboardInterrupt:
    client.disconnect()
    cur.execute("SELECT COUNT(*) FROM energy_live")
    print("received =", received)
    print("rows in energy_live =", cur.fetchone()[0])
    cur.close()
    conn.close()
