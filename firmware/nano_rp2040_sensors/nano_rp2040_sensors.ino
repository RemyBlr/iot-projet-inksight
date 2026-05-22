/*
 * Nano RP2040 Connect
 * Humidité sol + Température
 *
 * Branchements :
 *
 *   Capteur humidité (capacitif) :
 *     A.OUT → A0 (GP26)
 *     VCC   → VIN (5V)
 *     GND   → GND
 *
 *   Thermistor NTC 10kΩ (diviseur de tension) :
 *     3V3 ──[ 10kΩ ]──┬── A1 (GP27)
 *                     │
 *                   [NTC]
 *                     │
 *                    GND
 */

#include <math.h>
#include "./config.h"
#include "./utils.h"

// Calibration humidité
const int   MOISTURE_PIN = A0;
const int   ADC_DRY      = 1023;
const int   ADC_WET      = 639;

// Paramètres thermistor pour la température
const int   TEMP_PIN     = A1;
const float R_FIXED      = 10000.0;
const float R_NOMINAL    = 10000.0;
const float T_NOMINAL    = 25.0;
const float B_COEFF      = 3950.0;

// Intervalle de publication
const long PUBLISH_INTERVAL = 30000;  // ms
unsigned long lastPublish   = 0;

// Setup
void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 3000);
  // 12-bit pour le thermistor (0–4095)
  analogReadResolution(12);
  connectWifi();
  connectMqtt();
}

// Loop
void loop() {
  ensureConnected();

  if (millis() - lastPublish >= PUBLISH_INTERVAL) {
    lastPublish = millis();
    publishMoisture();
    publishTemperature();
  }
}

// Humidité
float readMoisturePct() {
  // analogReadResolution est en 12-bit, ramener en 10-bit pour la calibration
  int raw = analogRead(MOISTURE_PIN) >> 2;
  float pct = (float)(ADC_DRY - raw) / (ADC_DRY - ADC_WET) * 100.0;
  return constrain(pct, 0.0, 100.0);
}

void publishMoisture() {
  float value = readMoisturePct();

  String payload = "{\"value\":"  + String(value, 1) +
                   ",\"unit\":\"%\""                  +
                   ",\"label\":\"Humidite sol\"}";

  mqttClient.beginMessage("iot/sensors/soil_moisture");
  mqttClient.print(payload);
  mqttClient.endMessage();

  Serial.print("soil_moisture : ");
  Serial.print(value, 1);
  Serial.println("%");
}

// Température
float readTemperatureC() {
  int   raw    = analogRead(TEMP_PIN);  // 0–4095 (12-bit)
  float adcMax = 4095.0;

  if (raw == 0 || raw == (int)adcMax) return NAN;

  float rNtc    = R_FIXED * raw / (adcMax - raw);
  float t0K     = T_NOMINAL + 273.15;
  float tempK = 1.0 / ((1.0 / t0K) + (1.0 / B_COEFF) * log(rNtc / R_NOMINAL));
  float tempC = tempK - 273.15;

  return tempC;
}

void publishTemperature() {
  float value = readTemperatureC();

  if (isnan(value)) {
    Serial.println("Température : lecture invalide, skip");
    return;
  }

  String payload = "{\"value\":"  + String(value, 1)   +
                   ",\"unit\":\"\\u00b0C\""              +
                   ",\"label\":\"Temperature\"}";

  mqttClient.beginMessage("iot/sensors/temp_salon");
  mqttClient.print(payload);
  mqttClient.endMessage();

  Serial.print("temperature : ");
  Serial.print(value, 1);
  Serial.println("°C");
}
