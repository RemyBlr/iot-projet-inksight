"""
Client MQTT
Écoute les messages du Nano RP2040
Topics attendus : iot/sensors/<sensor_id>
Payload JSON : { "value": 72.3, "unit": "%", "label": "Humidité du sol" }
"""
import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING

try:
    import aiomqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False
    print("aiomqtt non installé, MQTT désactivé. pip install aiomqtt")

if TYPE_CHECKING:
    from modules.state import AppState

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_PREFIX = "iot/sensors/#"


async def start_mqtt_client(state: "AppState"):
    if not HAS_MQTT:
        return

    print(f"MQTT : connexion à {BROKER_HOST}:{BROKER_PORT}")
    while True:
        try:
            async with aiomqtt.Client(BROKER_HOST, BROKER_PORT) as client:
                await client.subscribe(TOPIC_PREFIX)
                print("MQTT connecté, écoute sur iot/sensors/#")
                async for message in client.messages:
                    _handle_message(state, str(message.topic), message.payload)
        except Exception as e:
            print(f"MQTT erreur : {e}, reconnexion dans 5s")
            await asyncio.sleep(5)


def _handle_message(state: "AppState", topic: str, payload: bytes):
    """
    Traite un message MQTT entrant
    Topic format : iot/sensors/<sensor_id>
    """
    try:
        parts = topic.split("/")
        if len(parts) < 3:
            return
        sensor_id = parts[2]

        data = json.loads(payload.decode("utf-8"))

        # Merge avec l'état existant du capteur, pour ne pas écraser les champs non fournis (ex: label)
        existing = state.sensors.get(sensor_id, {})
        state.sensors[sensor_id] = {
            **existing,
            **data,
            "updated_at": datetime.now().isoformat(),
        }
        print(f"Capteur '{sensor_id}' mis à jour : {data}")
    except Exception as e:
        print(f"MQTT message invalide ({topic}): {e}")
