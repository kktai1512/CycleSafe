#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <Arduino_JSON.h>
#include <PubSubClient.h>

const char* ssid = "taikahkiang"; //Your Wifi's SSID
const char* password = "taikahkiang"; //Wifi Password

// MQTT Broker
//const char *mqtt_broker = "broker.emqx.io";
const char *mqtt_broker = "192.168.139.156";
const char *mqtt_username = "emqx_ljw";
const char *mqtt_password = "public_ljw";
const int mqtt_port = 1883;

#define buzzer D5
#define SWITCH D6
#define red D3
#define green D7
#define led3 D8

//buzzer
int beats = 1;
int tempo = 50;
float sinVal;
int toneVal;
int x = 0;



volatile long LastPush = 0; //time when button was last pushed
volatile long DebounceDelay = 200; //160ms delay to debounce button
volatile byte state = LOW;
int ring_counter = 0;
int ring_timer = 0;
int first_ring = 0;
boolean has_sent = false;
WiFiClient espClient;
PubSubClient client(espClient);

IRAM_ATTR void toggle() {
  if ((millis() - LastPush) > DebounceDelay) {
    //state = !state;
    state = HIGH;
    LastPush = millis(); //record current time
  }
}

int result_fall;
String result_vehicle;
void callback(char* topic, byte* payload, unsigned int length) {
  if (strcmp(topic, "esp8266/car_led/esp8266-client-wemos/out") == 0) {
    Serial.print("Data Received From Vehicle Detection:");
    //result_vehicle = "";
    for (int i = 0; i < length; i++) {
      result_vehicle += (char)payload[i];
    }
    Serial.print(result_vehicle);
    Serial.print("\n");
  }

  else if (strcmp(topic, "esp8266/fall-actuator/esp8266-client-AC:0B:FB:D9:78:7B/out") == 0) {
    String payload_final = "";
    Serial.print("Data Received From Fall Detector:");
    for (int i = 0; i < length; i++) {
      payload_final += (char)payload[i];
    }
    Serial.print(payload_final);
    Serial.print("\n");
    if (payload_final == "fall") {
      result_fall = 1;
      has_sent = false;
    }

    state = LOW;

  }
}

void setup() {
  // Set software serial baud to 115200;
  Serial.begin(115200);
  // connecting to a WiFi network
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi..");
  }
  Serial.println("Connected to the WiFi network");
  //connecting to a mqtt broker
  client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(callback);
  while (!client.connected()) {
    Serial.println("Connecting to MQTT...");
    if (client.connect("ESP32Client", mqtt_username, mqtt_password ))
    {
      Serial.println("connected to MQTT broker");
    }
    else
    {
      Serial.print("failed with state ");
      Serial.print(client.state());
      delay(500);
    }
  }
  client.subscribe("esp8266/fall-actuator/esp8266-client-AC:0B:FB:D9:78:7B/out");  //subscribe to fall detection result
  client.subscribe("esp8266/car_led/esp8266-client-wemos/out"); //subscribe to vehicle detection result
  pinMode(buzzer, OUTPUT);
  pinMode(SWITCH, INPUT_PULLUP);
  pinMode(red, OUTPUT);
  pinMode(green, OUTPUT);
  pinMode(led3, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(SWITCH), toggle, RISING);
}

void loop() {
  if ((result_fall == 1) && (state == LOW)) { //predict fall && no push button
    ring_counter += 1;
    ring_timer = millis();
    for (int x = 0; x < 180; x++) {
      int i = 1, duration;
      duration = beats * tempo;  // length of note/rest in ms
      // convert degrees to radians then obtain sin value
      sinVal = (sin(x * (3.1412 / 180)));
      // generate a frequency from the sin value
      toneVal = 2000 + (int(sinVal * 1000));
      tone(buzzer, toneVal, duration);  // tone(pin, frequency, duration)
      delay(tempo / 10);            // brief pause between notes
    }

  }
  else if ((state == HIGH)) { //predict no fall or push button
    analogWrite (buzzer, 0);
    ring_counter = 0;
    state = LOW;
    client.publish("esp8266/fall-actuator/esp8266-client-AC:0B:FB:D9:78:7B/out", "backup");
    result_fall = 0; //reset state for next prediction
  }

  if (ring_counter == 1) { //first ring
    first_ring = millis();
  }
  if ((ring_timer - first_ring >= 20000) && (state == LOW) && has_sent == false) {
    Serial.print("Person in danger!!\n");
    client.publish("esp8266/fall-actuator/esp8266-client-AC:0B:FB:D9:78:7B/out", "emergency");
    has_sent = true;

  }

  if (result_vehicle == "car-danger") {
    digitalWrite(red, HIGH);
    digitalWrite(green, HIGH);
    digitalWrite(led3, HIGH);
    delay(500);
    result_vehicle = "";
  }
  else if (result_vehicle == "car-approaching") {
    digitalWrite(red, LOW);
    digitalWrite(green, LOW);
    digitalWrite(led3, HIGH);
    result_vehicle = "";
  }
  else if (result_vehicle == "car-near") {
    digitalWrite(red, LOW);
    digitalWrite(green, HIGH);
    digitalWrite(led3, HIGH);
    result_vehicle = "";
  }
  else if (result_vehicle == "car-safe") {
    digitalWrite(red, LOW);
    digitalWrite(green, LOW);
    digitalWrite(led3, LOW);
    result_vehicle = "";
  }
  client.loop();

}
