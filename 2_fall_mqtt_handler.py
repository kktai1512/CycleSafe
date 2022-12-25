from csv import writer
from datetime import datetime
from collections import deque
import numpy as np
import paho.mqtt.client as mqtt
import json
import requests

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to broker.")
        client.subscribe("esp8266/fall-actuator/esp8266-client-AC:0B:FB:D9:78:7B/out") # set own MAC address
    else:
        print("Connection failed with code: %d." % rc)

def on_message(client, userdata, msg):
    body = msg.payload.decode("utf-8")
    if body == "fall":
        print("initial")
        response = requests.get("http://127.0.0.1:5000/fall")
        print(response)
    elif body == "emergency":
        print("emergency")
        response = requests.get("http://127.0.0.1:5000/emergency")
        print(response)
    elif body == "backup":
        print("backup")
        response = requests.get("http://127.0.0.1:5000/back-up")
        print(response)


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