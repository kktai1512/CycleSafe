#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <Arduino_JSON.h>
#include <PubSubClient.h>

const char* ssid = "JingWoon"; //Your Wifi's SSID
const char* password = "12345678910"; //Wifi Password

// MQTT Broker
//const char *mqtt_broker = "broker.emqx.io";
const char *mqtt_broker = "172.20.10.12";
const char *mqtt_username = "emqx_ljw";
const char *mqtt_password = "public_ljw";
const int mqtt_port = 1883;

#define buzzer D6
#define SWITCH D5
volatile long LastPush = 0; //time when button was last pushed
volatile long DebounceDelay = 200; //160ms delay to debounce button
volatile byte state = LOW;
int ring_counter = 0;
int ring_timer = 0;
int first_ring = 0;

WiFiClient espClient;
PubSubClient client(espClient);

IRAM_ATTR void toggle() {
  if ((millis()-LastPush) > DebounceDelay){
    //state = !state;
    state = HIGH;
    LastPush = millis(); //record current time
    }
}

int result;
void callback(char* topic, byte* payload, unsigned int length) {

  //Serial.print("Message received in topic: ");
  //Serial.print(topic);
  //Serial.print("   length is:");
  //Serial.println(length);

  String payload_final;
  Serial.print("Data Received From Broker:");
  for (int i = 0; i < length; i++) {
    //Serial.print((char)payload[i]);
    payload_final += (char)payload[i];
  }
  Serial.print(payload_final);
  Serial.print("\n");
  result = payload_final[1] - '0';
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
  client.subscribe("esp8266/fall_actuator/esp8266-client-/out");  //subscribe to model prediction result
  pinMode(buzzer, OUTPUT);
  pinMode(SWITCH, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SWITCH),toggle, RISING);
}

void loop() {
  if ((result == 1) && (state == LOW)){ //predict fall && no push button
    ring_counter += 1;
    ring_timer = millis();
    analogWrite (buzzer, 255);
    delay (50);
    analogWrite (buzzer, 0);
    delay (10);
    analogWrite (buzzer, 100);
    delay (50); 
  }
  else if ((result == 0) || (state == HIGH)){ //predict no fall or push button
    analogWrite (buzzer, 0);
    ring_counter = 0;
    //state = LOW;  //reset state for next prediction
  }

  if (ring_counter == 1){ //first ring
    first_ring = millis();
  }
  if ((ring_timer - first_ring >= 20000) && (state == LOW)){
    //Serial.print("Person in danger!!\n");
    client.publish("esp8266/fall_actuator/esp8266-client-/post_action", "Person in danger!!");
  }
  client.loop();

}
