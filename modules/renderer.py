"""
Renderer
Construit le HTML de l'écran e-ink et le convertit en image via Playwright.

HTML  →  Playwright (screenshot PNG 24-bit)
      →  Pillow grayscale → 1-bit Floyd-Steinberg dithering
      →  BMP 1-bit  (servi à l'ESP32 via GxEPD2)
      →  PNG preview conservé pour l'UI de gestion

Résolution TRMNL OG : 800 x 480 px

Aidé par Claude pour _png_to_1bit_bmp
"""
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from modules.state import AppState

OUTPUT_DIR = Path("/tmp/trmnl_render")
OUTPUT_DIR.mkdir(exist_ok=True)

CSS_PATH    = Path(__file__).parent.parent / "static" / "screen.css"

SCREEN_W = 800
SCREEN_H = 480


#############################################################
###################### Génération HTML ######################
#############################################################

def build_screen_html(state: "AppState") -> str:
    """
    Assemble le HTML selon l'ordre et la visibilité des widgets
    """
    css = CSS_PATH.read_text(encoding="utf-8")

    widgets_html = ""
    visible = sorted(
        [w for w in state.layout["widgets"] if w.get("visible", True)],
        key=lambda w: w.get("order", 99),
    )
    for widget in visible:
        wtype = widget["type"]
        if wtype == "calendar":
            widgets_html += _render_calendar_widget(state)
        elif wtype == "sensor":
            sid = widget.get("sensor_id", "")
            sensor = state.sensors.get(sid)
            if sensor:
                widgets_html += _render_sensor_widget(sensor, sid)
        elif wtype == "clock":
            widgets_html += _render_clock_widget()

    return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                body {{ width: {SCREEN_W}px; height: {SCREEN_H}px; }}
                {css}
                </style>
            </head>
            <body>
                {widgets_html}
            </body>
        </html>"""


def _render_calendar_widget(state: "AppState") -> str:
    """
    Rend le widget calendrier avec les événements à venir (dans les X prochains jours)
    """
    now = datetime.now()
    days_ahead = state.config.get("calendar_days_ahead", 5)

    upcoming = [
        # Tous les events à venir dans les X prochains jours, triés par date
        ev for ev in state.calendar_events
        if _is_upcoming(ev, now, days_ahead)
    ]

    if not upcoming:
        rows = '<div class="empty">Aucun événement à venir</div>'
    else:
        rows = "".join(_render_event_row(ev) for ev in upcoming[:6])

    return f"""
        <div class="widget" style="flex:2">
          <div class="widget-title">Calendrier</div>
          <div class="calendar-events">{rows}</div>
        </div>"""


def _is_upcoming(ev: dict, now: datetime, days_ahead: int) -> bool:
    try:
        dt = datetime.fromisoformat(ev["dtstart"])
        return dt >= now and (dt - now).days <= days_ahead
    except Exception:
        return False


def _render_event_row(ev: dict) -> str:
    dt = datetime.fromisoformat(ev["dtstart"])
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
    display_val = f"{value:.0f}" if value is not None else "—"
    updated_str = ""
    if updated:
        try:
            updated_str = f"Mis à jour {datetime.fromisoformat(updated).strftime('%H:%M')}"
        except Exception:
            pass
    return f"""
        <div class="widget" style="flex:1">
          <div class="widget-title">{label}</div>
          <div class="sensor-value">{display_val}<span class="sensor-unit">{unit}</span></div>
          <div class="sensor-updated">{updated_str}</div>
        </div>"""


def _render_clock_widget() -> str:
    """
    Rend le widget horloge avec l'heure et la date du jour
    """
    now = datetime.now()
    return f"""
        <div class="widget" style="flex:0 0 auto">
          <div class="clock-time">{now.strftime("%H:%M")}</div>
          <div class="clock-date">{now.strftime("%A %d %B %Y")}</div>
        </div>"""


###########################################################################################
######################  HTML → PNG (Playwright) → BMP 1-bit (Pillow) ######################
###########################################################################################

async def render_screen_to_image(state: "AppState") -> Path:
    """
    Retourne le BMP 1-bit pour l'ESP32
    Le PNG intermédiaire est conservé dans OUTPUT_DIR pour une prévisualisation
    """
    png_path = await _playwright_screenshot(state)
    return _png_to_1bit_bmp(png_path)


async def render_screen_to_png(state: "AppState") -> Path:
    """
    Retourne uniquement le PNG
    """
    return await _playwright_screenshot(state)


async def _playwright_screenshot(state: "AppState") -> Path:
    """
    Génère le HTML et prend un screenshot Playwright → PNG 24-bit
    """
    from playwright.async_api import async_playwright

    html_path = OUTPUT_DIR / "screen.html"
    html_path.write_text(build_screen_html(state), encoding="utf-8")
    out_path = OUTPUT_DIR / "screen.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": SCREEN_W, "height": SCREEN_H})
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
    Convertit un PNG 24-bit en BMP 1-bit (noir/blanc)

    L'écran e-ink ne peut afficher que 2 valeurs, noir ou blanc (1 bit par pixel).

    Floyd-Steinberg diffuse l'erreur de quantification vers les pixels voisins,
    ce qui simule les niveaux de gris et donne un rendu beaucoup plus lisible,
    les bords de polices sont nets, les zones mi-tons restent lisibles.

    Étapes :
      1. RGB → L (grayscale, Luma ITU-R BT.601)
      2. L → 1 (1-bit, dithering Floyd-Steinberg, seuil implicite 127)
      3. Sauvegarde BMP Windows non compressé → directement lisible par GxEPD2

    Pour ajuster si l'image est trop sombre/claire sur l'écran réel :
      - Décommenter le bloc ImageEnhance.Contrast ci-dessous
      - Ou utiliser ImageEnhance.Brightness
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
