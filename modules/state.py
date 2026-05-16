"""
État global en mémoire
Remplace la base de données.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    # Event calendrier parsés depuis .ics
    calendar_events: list[dict] = field(default_factory=list)

    # Capteurs
    sensors: dict[str, Any] = field(default_factory=lambda: {
        "soil_moisture": {
            "label": "Humidité du sol",
            "value": None,
            "unit": "%",
            "updated_at": None,
        }
    })

    # Disposition des widgets à l'écran
    layout: dict = field(default_factory=lambda: {
        "widgets": [
            {"id": "calendar", "type": "calendar", "visible": True, "order": 0},
            {"id": "soil_moisture", "type": "sensor", "sensor_id": "soil_moisture", "visible": True, "order": 1},
            {"id": "clock", "type": "clock", "visible": True, "order": 2},
        ]
    })

    # Config globale
    config: dict = field(default_factory=lambda: {
        # ESP32 se réveille toutes les 6 heures
        "refresh_seconds": 300,
        "timezone": "Europe/Zurich",
        # Nbr de jours à afficher
        "calendar_days_ahead": 5,
    })
