# Section 1.3 - pilot publisher: send first 2000 readings over MQTT at QoS 1
import json
import time
import paho.mqtt.client as mqtt
import smart_meter_simulator

acked = 0

def on_publish(client, userdata, mid):
    global acked
    acked += 1

client = mqtt.Client(client_id="pilot_pub", clean_session=True)
client.on_publish = on_publish
client.connect("127.0.0.1", 1883, 60)
client.loop_start()

generator_count = 0
publish_queued = 0

for reading in smart_meter_simulator.iter_readings():
    generator_count += 1
    topic = "energy/meters/" + str(reading["meter_id"])
    payload = json.dumps(reading)
    client.publish(topic, payload, qos=1)
    publish_queued += 1
    time.sleep(0.001)   # tiny pause so the subscriber can keep up
    if generator_count >= 2000:
        break

# wait for all broker acks
while acked < publish_queued:
    time.sleep(0.1)

client.loop_stop()
client.disconnect()

print("generator_dicts =", generator_count)
print("publish_queued  =", publish_queued)
print("broker_acked    =", acked)
