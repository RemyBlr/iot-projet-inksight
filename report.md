---
title: "Rapport de projet - Inksight"
author: Bleuer Rémy, Rajadurai Thirusan
date: 28.05.2026
geometry: margin=2cm
output: pdf_document
---

## Introduction

InkSight, jeu de mot sur le mot anglais "Insight" qui signifie "avoir une vue globale sur un sujet" et "Ink" qui fait référence à notre écran e-ink. C'est un tableau de bord IoT local qui affiche des données en temps réel sur un écran e-ink. Le projet vise à centraliser sur un écran sobre et à basse consommation, des informations utiles au quotidien, comme un calendrier personnel, humidité du sol et température ambiante.

L'ensemble du système fonctionne en réseau local, sans aucune dépendance à un service externe. Toute la logique est hébergée sur un Raspberry pi 5, qui a pour utilité aussi de collecter les données des capteurs et de générer l'image pour l'écran.

---

## Matériel utilisé

| Composant | Modèle | Rôle |
|---|---|---|
| Serveur | Raspberry Pi 5 (16 Go RAM) | Logique applicative, API REST, rendu image |
| Écran | TRMNL OG (ESP32) | Affichage e-ink 800×480 px, polling |
| Microcontrôleur | Arduino Nano RP2040 Connect | Lecture capteurs, envoi MQTT |
| Capteur humidité | Capteur capacitif NE555 (5V) | Humidité du sol |
| Capteur température | Thermistor NTC 10 kΩ | Température ambiante |

---

## Architecture générale

```
┌─────────────────────────────────────────────────────┐
│                   Réseau local Wi-Fi                │
│                                                     │
│  ┌──────────────┐        MQTT         ┌──────────┐  │
│  │ Nano RP2040  │ ──────────────────► │          │  │
│  │  (capteurs)  │  iot/sensors/#      │          │  │
│  └──────────────┘                     │  Pi 5    │  │
│                                       │ FastAPI  │  │
│  ┌──────────────┐   GET /display/     │          │  │
│  │  TRMNL OG    │ ◄────────────────── │          │  │
│  │   (ESP32)    │   image + config    │          │  │
│  └──────────────┘                     └──────────┘  │
│                                            ▲        │
│  ┌──────────────┐        HTTP              │        │
│  │  Navigateur  │ ───────────────────────► │        │
│  │  (gestion)   │   localhost:8000         │        │
│  └──────────────┘                          │        │
└─────────────────────────────────────────────────────┘
```

On a trois flux sur notre réseaux :

- ***Captuers vers Pi*** : le Nano RP2040 publis les valeurs sur des capteurs toutes les 30s via MQTT sur les topics `iot/sensors/soil_moisture` et `iot/sensors/temperature`
- ***Pi vers l'écran*** : TODO
- ***Navigateur vers Pi*** : une interface est disponible sur `http://localhost:8000` et permet de configurer les widgets, d'uploader le calendrier `.ics`, de modifier l'interface et de prévisualiser le rendu

---

## Choix d'implémentations

### Serveur avec FastAPI et Python

Le serveur tourne sur le Pi 5 et expose une API REST. `FastAPI` a été choisi pour sa légérté et son support de l'asynchrone qui est nécessaire pour le client MQTT en parallèle.

### Absence de base de donnée

Garder l'état en mémoire simplifie le déploiement et la maintenance pour un projet que l'on garde en local. La sérialisation sur disque est à prévoir dans une version future.  Les valeurs des capteurs, la config et le layout sont conservés en RAM dans une dataclass `AppState`. Un redémarrage du serveur ne présente pas de perte critique de données.

### Rendu de l'image

L'écran e-ink n'accepte que des images bitmap 1bit, donc des images en noir et blanc. On applique l'algorithme de dithering de Floyd-Steinberg pour convertir les images en 1bit tout en préservant les détails. Voici les outils utilisés pour le rendu :

***Playwright*** pour le rendu HTML/CSS en image. C'est une solution simple pour faire du layout dynamique et facilement modifiable, sans se soucier de la génération d'image. Le serveur génère une page HTML avec les données et la config, puis Playwright capture un screenshot de la page.

***Pillow*** pour le post-traitement de l'image. Après le rendu, on convertit l'image en mode 1bit et on la redimensionne à la résolution de l'écran (800×480 px).

### Communication avec MQTT

Le Nano RP2040 publie ses mesures sur un borker Mosquitto local (hébergé sur le Pi 5). Le protocole MQTT est léger et adapté pour les microcontrôleurs, et permet une communication asynchrone efficace entre les capteurs et le serveur. Il est conçu pour l'IoT et est donc un choix naturel pour ce projet. Le pattern de publication sur des topics spécifiques (`iot/sensors/#`) permet une organisation claire des données, il est facile d'ajouter de nouveaux capteurs à l'avenir sans modifier la logique de communication.

### Capteur d'humidité

Le capteur capacitif NE555 nécessite 5V, ce qui n'est pas possible sur le Nano RP2040 qui est limité à 3.3V. On a donc branché sur le VIN du Nano, qui est alimenté en 5V. Avec un multimètre, on arrive à 3.4V sur la broche du signal, on dépasse très légèrement les 3.3V.

La lecture ADC retourne des valeurs inversées, sec retourne une valeur haute, alors que humide retourne une valeur basse. Il faut caliber le capteur avant de pouvoir l'utiliser, voici les valeurs obtenues :

| État | Valeur ADC (10-bit) |
|---|---|
| Sec (air libre) | 1023 |
| Mouillé (eau) | 639 |

### Capteur de température

Le thermistor NTC 10 kΩ est monté en diviseur de tension avec une résistance de 10 kΩ alimenté en 3.3V. L'équation de Steinhart-Hart est utilisée pour convertir la valeur ADC en température en degrés Celsius.

```
1/T = 1/T₀ + (1/B) × ln(R/R₀)
```

L'ADC est configuré en 12--bits pour une meilleure précision sur la plage 0-3.3V.

### Interface de gestion

L'interface web est une single page en html/css, sans framework, conçue avec l'aide de Claude. On a un layout de l'écran qui est configurable via des pressets CSS. Chaque widget peut occuper plusieurs lignes ou colones. Le preset actif et la config des widget sont stockés dans `AppState.layout` et sont persistés via l'API.

---

## Améliorations futures

- ***Persistance*** : sérialiser l'état sur disque pour survivre au redémarrage du serveur, pareil pour le calendrier
- ***Sécurité*** : le serveur n'a pas d'auth, on est en réseau local, mais point à améliorer sur on veut exposer notre projet
- ***Application*** : étendre le manager sur une application mobile pour configurer à distance et recevoir des notifications
- ***Changement matériel*** : prendre un microcontrôleur qui accepte du 5V, ou trouver un capteur d'humidité compatible 3.3V pour éviter les risques de surtension
