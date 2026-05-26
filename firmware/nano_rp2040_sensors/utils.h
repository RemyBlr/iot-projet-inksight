// shared/utils.h
// Fonctions WiFi et MQTT communes aux deux sketches

#pragma once

#include <WiFiNINA.h>
#include <ArduinoMqttClient.h>

WiFiClient  wifiClient;
MqttClient  mqttClient(wifiClient);

void connectWifi() {
  Serial.print("WiFi : connexion à ");
  Serial.print(WIFI_SSID);
  Serial.print("…");

  while (WiFi.begin(WIFI_SSID, WIFI_PASSWORD) != WL_CONNECTED) {
    Serial.print(".");
    delay(2000);
  }

  Serial.println(" OK");
  Serial.print("IP : ");
  Serial.println(WiFi.localIP());
}

void connectMqtt() {
  Serial.print("MQTT : connexion à ");
  Serial.print(MQTT_BROKER);
  Serial.print("…");

  while (!mqttClient.connect(MQTT_BROKER, MQTT_PORT)) {
    Serial.print(".");
    delay(2000);
  }

  Serial.println(" OK");
}

void ensureConnected() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi perdu — reconnexion…");
    connectWifi();
  }
  if (!mqttClient.connected()) {
    Serial.println("MQTT perdu — reconnexion…");
    connectMqtt();
  }
  mqttClient.poll();
}
