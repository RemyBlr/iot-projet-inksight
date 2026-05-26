"""
Renderer
Construit le HTML de l'écran e-ink et le convertit en image via Playwright.

HTML  ->  Playwright (screenshot PNG 24-bit)
      ->  Pillow grayscale -> 1-bit Floyd-Steinberg dithering
      ->  BMP 1-bit  (servi à l'ESP32 via GxEPD2)
      ->  PNG preview conservé pour l'UI de gestion

Résolution TRMNL OG : 800 x 480 px
Le style de l'écran est dans static/screen.css

Aidé par Claude pour _png_to_1bit_bmp
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from modules.state import AppState

OUTPUT_DIR = Path("/tmp/trmnl_render")
CSS_PATH   = Path(__file__).parent.parent / "static" / "screen.css"
OUTPUT_DIR.mkdir(exist_ok=True)

SCREEN_W = 800
SCREEN_H = 480


#############################################################
###################### Génération HTML ######################
#############################################################

def build_screen_html(state: "AppState") -> str:
    """
    Assemble le HTML selon le preset de grille et la visibilité des widgets.
    """
    from modules.state import LAYOUT_PRESETS

    css = CSS_PATH.read_text(encoding="utf-8")

    preset_id = state.layout.get("preset", "1col")
    preset = LAYOUT_PRESETS.get(preset_id, LAYOUT_PRESETS["1col"])

    visible = sorted(
        [w for w in state.layout["widgets"] if w.get("visible", True)],
        key=lambda w: w.get("order", 99),
    )

    widgets_html = "".join(_render_widget(w, state, preset) for w in visible)

    grid_css = preset["css_grid"]

    return f"""<!DOCTYPE html>
                <html>
                <head>
                  <meta charset="utf-8">
                  <style>
                    body {{ width: {SCREEN_W}px; height: {SCREEN_H}px; }}
                    .screen-grid {{ {grid_css} }}
                    {css}
                  </style>
                </head>
                <body>
                  <div class="screen-grid">
                    {widgets_html}
                  </div>
                </body>
                </html>"""



###########################################################
###################### Helper render ######################
###########################################################

def _render_widget(widget: dict, state: "AppState", preset: dict) -> str:
    """
    Dispatch vers le bon renderer selon le type du widget
    """
    wtype = widget["type"]

    span_col = widget.get("span_col", 1)
    span_row = widget.get("span_row", 1)
    style = ""
    if span_col > 1:
        style += f"grid-column: span {span_col};"
    if span_row > 1:
        style += f"grid-row: span {span_row};"

    inner = ""
    if wtype == "calendar":
        inner = _render_calendar_widget(state)
    elif wtype == "sensor":
        sid = widget.get("sensor_id", "")
        sensor = state.sensors.get(sid)
        if sensor:
            inner = _render_sensor_widget(sensor, sid)
    elif wtype == "clock":
        inner = _render_clock_widget()

    if not inner:
        return ""

    wrapper_style = f' style="{style}"' if style else ""
    return f'<div class="widget-cell"{wrapper_style}>{inner}</div>'


def _render_calendar_widget(state: "AppState") -> str:
    """
    Rend le widget calendrier avec les événements à venir (dans les X prochains jours)
    """
    now = datetime.now()
    days_ahead  = state.config.get("calendar_days_ahead", 14)
    days_behind = state.config.get("calendar_days_behind", 0)
    since = now - timedelta(days=days_behind)
    until = now + timedelta(days=days_ahead)

    upcoming = [ev for ev in state.calendar_events if _in_window(ev, since, until)]

    if not upcoming:
        rows = '<div class="empty">Aucun événement</div>'
    else:
        rows = "".join(_render_event_row(ev) for ev in upcoming[:8])

    return f"""
      <div class="widget-title">Calendrier</div>
      <div class="calendar-events">{rows}</div>"""


def _in_window(ev: dict, since: datetime, until: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(ev["dtstart"])
        return since <= dt <= until
    except Exception:
        return False


def _render_event_row(ev: dict) -> str:
    """
    Rend une ligne d'événement : date + titre
    """
    dt       = datetime.fromisoformat(ev["dtstart"])
    date_str = dt.strftime("%a %d %b %H:%M") if not ev.get("all_day") else dt.strftime("%a %d %b")
    return f"""
      <div class="event-row">
        <span class="event-date">{date_str}</span>
        <span class="event-title">{ev["summary"]}</span>
      </div>"""


def _render_sensor_widget(sensor: dict, sensor_id: str) -> str:
    """
    Rend le widget d'un capteur : valeur + unité + dernière mise à jour
    """
    value = sensor.get("value")
    unit = sensor.get("unit", "")
    label = sensor.get("label", sensor_id)
    updated = sensor.get("updated_at", "")
    display_val = f"{value:.1f}" if value is not None else "—"
    updated_str = _format_updated(updated)

    return f"""
      <div class="widget-title">{label}</div>
      <div class="sensor-value">{display_val}<span class="sensor-unit">{unit}</span></div>
      <div class="sensor-updated">{updated_str}</div>"""


def _format_updated(updated: str) -> str:
    """
    Met en forme la date de dernière mise à jour d'un capteur, au format "Mis à jour HH:MM"
    """
    if not updated:
        return ""
    try:
        return f"Mis à jour {datetime.fromisoformat(updated).strftime('%H:%M')}"
    except Exception:
        return ""


def _render_clock_widget() -> str:
    """
    Rend le widget horloge avec l'heure et la date du jour
    """
    now = datetime.now()
    return f"""
      <div class="clock-time">{now.strftime("%H:%M")}</div>
      <div class="clock-date">{now.strftime("%A %d %B %Y")}</div>"""


###########################################################################################
######################  HTML -> PNG (Playwright) -> BMP 1-bit (Pillow) ######################
###########################################################################################

async def render_screen_to_image(state: "AppState") -> Path:
    """
    Pipeline complet -> BMP 1-bit pour l'ESP32
    """
    png_path = await _playwright_screenshot(state)
    return _png_to_1bit_bmp(png_path)


async def render_screen_to_png(state: "AppState") -> Path:
    """
    PNG couleurs uniquement -> prévisualisation dans l'UI
    """
    return await _playwright_screenshot(state)


async def _playwright_screenshot(state: "AppState") -> Path:
    from playwright.async_api import async_playwright

    html_path = OUTPUT_DIR / "screen.html"
    html_path.write_text(build_screen_html(state), encoding="utf-8")
    out_path = OUTPUT_DIR / "screen.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page(viewport={"width": SCREEN_W, "height": SCREEN_H})
        await page.goto(f"file://{html_path.resolve()}")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path=str(out_path),
            clip={"x": 0, "y": 0, "width": SCREEN_W, "height": SCREEN_H},
        )
        await browser.close()

    return out_path


def _png_to_1bit_bmp(png_path: Path) -> Path:
    """
    PNG 24-bit -> BMP 1-bit avec dithering Floyd-Steinberg.
    Étapes : RGB -> grayscale (Luma BT.601) -> 1-bit -> BMP non compressé
    """
    bmp_path = OUTPUT_DIR / "screen.bmp"

    with Image.open(png_path) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Booster légèrement le contraste avant dithering
        from PIL import ImageEnhance
        img = ImageEnhance.Contrast(img).enhance(1.3)

        # Étape 1 : grayscale
        gray = img.convert("L")

        # Étape 2 : 1-bit avec Floyd-Steinberg
        mono = gray.convert("1", dither=Image.Dither.FLOYDSTEINBERG)

        # Étape 3 : BMP (non compressé, compatible GxEPD2)
        mono.save(str(bmp_path), format="BMP")

    print(f"BMP 1-bit : {bmp_path} ({bmp_path.stat().st_size // 1024} KB)")
    return bmp_path


def get_cached_bmp() -> Path | None:
    p = OUTPUT_DIR / "screen.bmp"
    return p if p.exists() else None


def get_cached_png() -> Path | None:
    p = OUTPUT_DIR / "screen.png"
    return p if p.exists() else None
