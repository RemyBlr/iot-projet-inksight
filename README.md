# iot-projet-inksight

Serveur local qui affiche un calendrier et des données capteurs sur un écran e-ink TRMNL OG.

## Matériel

| Appareil | Rôle |
|---|---|
| Raspberry Pi 5 | Serveur — logique, API, rendu image |
| TRMNL OG (ESP32) | Affichage e-ink — polling image toutes les N minutes |
| Nano RP2040 Connect | Capteur d'humidité du sol — envoi MQTT |

## Lancer sur Mac (développement)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
python main.py
```

Ouvrir `http://localhost:8000`.

## Structure

TODO completer
```
main.py                  # Serveur FastAPI — tous les endpoints
...
```

## Endpoints principaux

| Endpoint | Usage |
|---|---|
| `GET /` | UI de gestion |
| `GET /display/image` | BMP 1-bit pour l'ESP32 |
| `GET /display/preview-png` | PNG couleur pour la prévisualisation |
| `GET /display/config` | Timer + URL image pour l'ESP32 |
| `POST /calendar/upload` | Upload fichier `.ics` |
| `GET /sensors` | Valeurs capteurs actuelles |
| `POST /sensors/{id}` | Mise à jour manuelle d'un capteur |

## Variables d'environnement (`.env`)

| Variable | Défaut | Description |
|---|---|---|
| `ENV` | `mac` | `mac` ou `pi` |
| `HOST_IP` | `localhost` | IP vue par l'ESP32 et le Nano |
| `PORT` | `8000` | Port du serveur |
| `MQTT_BROKER` | `localhost` | IP du broker Mosquitto |