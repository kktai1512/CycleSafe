#include <ESP8266WiFi.h>

#include <PubSubClient.h>
#include <SPI.h>
#include <Ethernet.h>

#include <WiFiClient.h>
#include <ArduinoJson.h>

#include <MPU6500_WE.h>
#include <Wire.h>

#include <FS.h>
#include <LittleFS.h>
#include <CertStoreBearSSL.h>

#define MPU6500_ADDR 0x68

#define TILT_LEFT D5
#define TILT_RIGHT D6
#define SWITCH D7
#define LED D8

// WiFi Information
const char* ssid = "taikahkiang"; //Your Wifi's SSID
const char* password = "taikahkiang"; //Wifi Password

// MQTT Broker
//const char *mqtt_broker = "broker.emqx.io";
//const char *mqtt_broker = "192.168.242.156";
//const char *topic = "esp8266/data_collection";
const char *mqtt_broker = "6e96094f023344efa89e7be0a2e9716b.s2.eu.hivemq.cloud";
const char *topic = "esp8266/data_collection";
const char *mqtt_username = "";
const char *mqtt_password = "";
const int mqtt_port = 8883;

BearSSL::CertStore certStore;

WiFiClientSecure wifiClient;
PubSubClient * client;

MPU6500_WE myMPU6500 = MPU6500_WE(MPU6500_ADDR);

volatile byte state = HIGH;
volatile unsigned long prev_interrupt_time = 0;
IRAM_ATTR void toggle() {
  volatile unsigned long interrupt_time = millis();
  if (interrupt_time - prev_interrupt_time >= 300) {
    state = !state;
    digitalWrite(LED, !state);
    prev_interrupt_time = interrupt_time;
  }
}

String client_id = "esp8266-client-";
void setup(void) {
  Serial.begin(115200);
  delay(3000);
  LittleFS.begin();
  WiFi.begin(ssid, password);
  Wire.begin();
  Serial.println("");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  int numCerts = certStore.initCertStore(LittleFS, PSTR("/certs.idx"), PSTR("/certs.ar"));
  Serial.printf("Number of CA certs read: %d\n", numCerts);
  if (numCerts == 0) {
    Serial.printf("No certs found. Did you run certs-from-mozilla.py and upload the LittleFS directory before running?\n");
    return; // Can't connect to anything w/o certs!
  }

  BearSSL::WiFiClientSecure *bear = new BearSSL::WiFiClientSecure();
  // Integrate the cert store with this connection
  bear->setCertStore(&certStore);

  client = new PubSubClient(*bear);
  client->setServer(mqtt_broker, mqtt_port);

  pinMode(TILT_LEFT, INPUT);
  pinMode(TILT_RIGHT, INPUT);

  pinMode(SWITCH, INPUT_PULLUP);
  pinMode(LED, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(SWITCH), toggle, RISING);

  if (!myMPU6500.init()) {
    Serial.println("MPU6500 does not respond");
  }
  
  else {
    Serial.println("MPU6500 is connected");
  }
  
  Serial.println("Position you MPU6500 flat and don't move it - calibrating...");
  delay(1000);
  myMPU6500.autoOffsets();
  Serial.println("Done!");

  myMPU6500.enableGyrDLPF();
  myMPU6500.setGyrDLPF(MPU6500_DLPF_6);
  myMPU6500.setSampleRateDivider(5);
  myMPU6500.setGyrRange(MPU6500_GYRO_RANGE_250);
  myMPU6500.setAccRange(MPU6500_ACC_RANGE_2G);
  myMPU6500.enableAccDLPF(true);
  myMPU6500.setAccDLPF(MPU6500_DLPF_6);
  myMPU6500.enableAccAxes(MPU6500_ENABLE_XYZ);
  myMPU6500.enableGyrAxes(MPU6500_ENABLE_XYZ);
  delay(1000);
}

void reconnect() {
  // Loop until we’re reconnected
  while (!client->connected()) {
    Serial.print("Attempting MQTT connection…");
    String clientId = "ESP8266Client - MyClient";
    // Attempt to connect
    // Insert your password
    if (client->connect(clientId.c_str(), "cs3237", "cs3237abc")) {
      Serial.println("connected");
      // … and resubscribe
      client->subscribe("testTopic");
    } else {
      Serial.print("failed, rc = ");
      Serial.print(client->state());
      Serial.println(" try again in 2 seconds");
      // Wait 5 seconds before retrying
      delay(2000);
    }
  }
}

void loop(void) {
  if (WiFi.status() == WL_CONNECTED) {
    if (!client->connected()) {
      reconnect();
    }
    
    // data from sensors
    xyzFloat gValue = myMPU6500.getGValues();
    xyzFloat gyr = myMPU6500.getGyrValues();
    float resultantG = myMPU6500.getResultantG(gValue);

    float accX = gValue.x;
    float accY = gValue.y;
    float accZ = gValue.z;
    float accResultant = resultantG;
    float gyrX = gyr.x;
    float gyrY = gyr.y;
    float gyrZ = gyr.z;
    int tiltLeft = digitalRead(TILT_LEFT) == HIGH ? 0 : 1; // HIGH means switch open
    int tiltRight = digitalRead(TILT_RIGHT) == HIGH ? 0 : 1;
    int isFall = state == HIGH ? 0 : 1;

    String payload = "{\"accX\":";
    payload += String(accX);
    payload += ",\"accY\":";
    payload += String(accY);
    payload += ",\"accZ\":";
    payload += String(accZ);
    payload += ",\"accResultant\":";
    payload += String(accResultant);
    payload += ",\"gyrX\":";
    payload += String(gyrX);
    payload += ",\"gyrY\":";
    payload += String(gyrY);
    payload += ",\"gyrZ\":";
    payload += String(gyrZ);
    payload += ",\"tiltLeft\":";
    payload += String(tiltLeft);
    payload += ",\"tiltRight\":";
    payload += String(tiltRight);
    payload += ",\"isFall\":";
    payload += String(isFall);
    payload += "}"; 

    String pubTopic;
    pubTopic += topic;
    pubTopic += "/";
    pubTopic += client_id;
    pubTopic += "/out";
    int i = client->publish( (char*) pubTopic.c_str() , (char*) payload.c_str(), true );
    Serial.println(i);
    Serial.println(pubTopic);
    Serial.println(payload);
  } else {
    Serial.println("WiFi disconnected");
  }
  delay(100);
}
