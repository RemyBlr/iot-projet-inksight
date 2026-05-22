# Pi IoT Dashboard

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

```
.env.example                    # Exemple de configuration
main.py                         # Serveur FastAPI — tous les endpoints
modules/
  calendar_parser.py            # Parsing fichiers .ics
  mqtt_client.py                # Réception données capteurs via MQTT
  renderer.py                   # HTML → PNG (Playwright) → BMP 1-bit (Pillow)
  state.py                      # État en RAM (pas de base de données)
static/
  dashboard.css                 # Styles CSS du dashboard
  dashboard.js                  # Logique frontend (fetch API, interactions)
  index.html                    # UI de gestion
  screen.css                    # Styles spécifiques à l'écran e-ink
firmware/
  nano_rp2040_sensors/
    config.h.example            # Exemple de configuration pour le Nano RP2040
    nano_rp2040_sensors.ino     # Code Arduino pour le Nano RP2040 Connect
    utils.h                     # Fonctions utilitaires, wifi et mqtt
    
```

## Endpoints principaux

| Endpoint                   | Usage                                              |
|----------------------------|----------------------------------------------------|
| `GET /`                    | UI de gestion                                      |
| `GET /display/image`       | BMP 1-bit pour l'ESP32                             |
| `GET /display/preview-png` | PNG couleurs pour la prévisualisation              |
| `GET /display/preview`     | Prévisualtion de l'écran e-ink pour le debug       |
| `POST /calendar/upload`    | Upload fichier `.ics`                              |
| `GET /sensors`             | Valeurs capteurs actuelles                         |
| `POST /sensors/{id}`       | Mise à jour manuelle d'un capteur                  |
| `GET /config`              | Configuration actuelle (variables d'environnement) |
| `POST /config`             | Mise à jour de la configuration                    |
| `GET /layout`              | Layout de l'app                                    |
| `POST /layout`             | Mise à jour du layout de l'app                     |
| `GET /layout/presets`      | Liste tous les presets disponibles                 |

## Variables d'environnement (`.env`)

| Variable | Défaut | Description |
|---|---|---|
| `ENV` | `mac` | `mac` ou `pi` |
| `HOST_IP` | `localhost` | IP vue par l'ESP32 et le Nano |
| `PORT` | `8000` | Port du serveur |
| `MQTT_BROKER` | `localhost` | IP du broker Mosquitto |
