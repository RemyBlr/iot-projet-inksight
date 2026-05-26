"""
État global en mémoire
Remplace la base de données.
"""
from dataclasses import dataclass, field
from typing import Any


# Presets de disposition disponibles pour l'écran e-ink
# Chaque preset définit comment les widgets sont arrangés (CSS grid areas)
LAYOUT_PRESETS = {
    "1col": {
        "label": "Grille 1×3",
        "description": "Widgets empilés verticalement",
        "css_grid": "grid-template-columns: 1fr;",
        "areas": None,
    },

    # "2col": {
    #     "label": "2 colonnes",
    #     "description": "2 colonnes égales",
    #     "css_grid": "grid-template-columns: 1fr 1fr;",
    #     "areas": None,
    # },
    # "3col": {
    #     "label": "3 colonnes",
    #     "description": "3 colonnes égales",
    #     "css_grid": "grid-template-columns: 1fr 1fr 1fr;",
    #     "areas": None,
    # },
    # "2col-sidebar": {
    #     "label": "Contenu + sidebar",
    #     "description": "Colonne principale large + sidebar étroite",
    #     "css_grid": "grid-template-columns: 2fr 1fr;",
    #     "areas": None,
    # },

    "2x2": {
        "label": "Grille 2×2",
        "description": "4 cases égales",
        "css_grid": "grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;",
        "areas": None,
    },
    "3x2": {
        "label": "Grille 3×2",
        "description": "6 cases (3 colonnes, 2 lignes)",
        "css_grid": "grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 1fr 1fr;",
        "areas": None,
    },
    "3x3": {
        "label": "Grille 3×3",
        "description": "9 cases égales",
        "css_grid": "grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 1fr 1fr 1fr;",
        "areas": None,
    },
    "hero-bottom": {
        "label": "Hero + barre basse",
        "description": "Grande zone en haut, petites cases en bas",
        "css_grid": "grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 2fr 1fr;",
        "areas": '"hero hero hero" "a b c"',
    },
    "sidebar-grid": {
        "label": "Sidebar + grille 2×2",
        "description": "Sidebar gauche + 4 cases à droite",
        "css_grid": "grid-template-columns: 1fr 2fr; grid-template-rows: 1fr 1fr;",
        "areas": '"sidebar top-left top-right" "sidebar bottom-left bottom-right"',
    },
}


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

    # Widgets et leur placement dans la grille
    # col et row sont des indices 0-based dans la grille du preset actif
    # span_col / span_row permettent à un widget d'occuper plusieurs cases
    layout: dict = field(default_factory=lambda: {
        "preset": "1col",
        "widgets": [
            {
                "id": "calendar",
                "type": "calendar",
                "visible": True,
                "order": 0,
                "span_col": 1,
                "span_row": 1,
            },
            {
                "id": "soil_moisture",
                "type": "sensor",
                "sensor_id": "soil_moisture",
                "visible": True,
                "order": 1,
                "span_col": 1,
                "span_row": 1,
            },
            {
                "id": "clock",
                "type": "clock",
                "visible": True,
                "order": 2,
                "span_col": 1,
                "span_row": 1,
            },
        ],
    })

    # Config globale
    config: dict = field(default_factory=lambda: {
        # ESP32 se réveille toutes les 5 minutes de base
        "refresh_seconds": 300,
        "timezone": "Europe/Zurich",
        "calendar_days_ahead": 14,
        "calendar_days_behind": 0,
    })
