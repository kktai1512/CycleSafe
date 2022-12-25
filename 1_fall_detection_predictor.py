from csv import writer
from datetime import datetime
from collections import deque
import numpy as np
import paho.mqtt.client as mqtt
import json
from tensorflow.keras.models import load_model
import pickle

# with open('data.csv', 'a') as f:
#     writerObject = writer(f)
# writerObject = writer(open('pred_out.csv', 'a', newline=''))

MODEL_NAME = 'mlp.hd5'
model = load_model(MODEL_NAME)
queue = deque()

with open('scaler.pickle', 'rb') as f:
    scaler = pickle.load(f)

event_map = {
    0: "upright",
    1: "forward",
    2: "turn_left",
    3: "turn_right",
    4: "place_down",
    5: "lie",
    6: "back_up",
    7: "fall"
}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to broker.")
        client.subscribe("esp8266/data_collection/esp8266-client-AC:0B:FB:D9:78:7B/out") # set own MAC address
    else:
        print("Connection failed with code: %d." % rc)

def on_message(client, userdata, msg):
    recv_dict = json.loads(msg.payload)

    currentTime = datetime.utcnow().strftime('%F %T.%f')[:-3]
    params = ['accX', 'accY', 'accZ', 'accResultant', 'gyrX', 'gyrY', 'gyrZ', 'tiltLeft', 'tiltRight', 'isFall']
    dataRow = [currentTime]

    for p in params:
        dataStr = recv_dict[p]

        data = float(dataStr) # if dataStr else 0
        dataRow.append(data)

    arr = np.array(dataRow[1:8])
    queue.append(arr)
    output = checkQueue(recv_dict['accResultant'] > 1.3)
    if output == 7: # Fall
        client.publish("esp8266/fall-actuator/esp8266-client-AC:0B:FB:D9:78:7B/out", "fall") 

    # dataRow.append(output)
    # writerObject.writerow(dataRow)

def checkQueue(bool):
    if len(queue) < 10:
        return
    
    top10 = list(queue)[1:10]
    first = list(queue)[0]
    queue.popleft()

    if not bool:
        return 

    input = np.append(first, top10)
    input = np.array([input])
    input = scaler.transform(input)
    #print(input)

    output = np.argmax(model.predict(input))
    print('%d: %s' % (output, event_map[output]))
    return int(output)

def setup(hostname):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(hostname)
    client.loop_start()
    return client

def main():
    # setup("broker.emqx.io")
    setup('192.168.139.156') # set own IP address
    while True:
        pass

if __name__=='__main__':
    main()