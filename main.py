"""
Serveur IoT local
Configurer via .env
FastAPI + Playwright + MQTT
"""
import os
import asyncio
import time

from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from modules.state import AppState, LAYOUT_PRESETS
from modules.calendar_parser import parse_ics
from modules.renderer import render_screen_to_image, render_screen_to_png, build_screen_html
from modules.mqtt_client import start_mqtt_client

# Config depuis .env
HOST_IP = os.getenv("HOST_IP", "localhost")
PORT = int(os.getenv("PORT", "8000"))
ENV = os.getenv("ENV", "mac")

# Global state partagé
# On n'utilise pas de BD
state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage, on lance le client MQTT en background
    asyncio.create_task(start_mqtt_client(state))
    yield
    # Au shutdown, on ne fait rien de spécial

app = FastAPI(title="InkSight Server", lifespan=lifespan)

# On sert les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")


#####################################################################
###################### Endpoints pour le TRMNL ######################
#####################################################################

@app.get("/display/image")
async def get_display_image():
    """
    L'ESP32 appelle cet endpoint à chaque réveil
    Retourne le BMP 1-bit
    Format directement lisible par GxEPD2
    """
    bmp_path = await render_screen_to_image(state)
    return FileResponse(bmp_path, media_type="image/bmp")


@app.get("/display/preview-png")
async def get_preview_png():
    """
    Endpoint pour l'UI de gestion
    Régénère le screenshot mais sans la conversion BMP
    """
    from modules.renderer import render_screen_to_png, get_cached_png
    png_path = await render_screen_to_png(state)
    return FileResponse(png_path, media_type="image/png")


@app.get("/display/preview", response_class=HTMLResponse)
async def preview_html():
    """
    Prévisualiser le HTML brut dans le navigateur
    Permet d'accéder à l'inspecteur d'élément pour debug l'html
    """
    from modules.renderer import build_screen_html
    return HTMLResponse(content=build_screen_html(state))


#######################################################################
###################### Endpoints pour la gestion ######################
#######################################################################

@app.post("/calendar/upload")
async def upload_calendar(file: UploadFile = File(...)):
    """
    Upload d'un fichier .ics
    """
    if not file.filename.endswith(".ics"):
        raise HTTPException(400, "Seuls les fichiers .ics sont acceptés")
    content = await file.read()
    events = parse_ics(content.decode("utf-8"))
    state.calendar_events = events
    return {"status": "ok", "events_count": len(events)}


@app.get("/sensors")
async def get_sensors():
    """
    Retourne toutes les valeurs capteurs actuelles
    """
    return state.sensors


@app.post("/sensors/{sensor_id}")
async def update_sensor(sensor_id: str, payload: dict):
    """
    Met à jour manuellement un capteur, pour tester/debug
    En prod, le Nano RP2040 passe par MQTT.
    """
    state.sensors[sensor_id] = payload
    return {"status": "ok"}


@app.get("/config")
async def get_config():
    """
    Renvoie la configuration de l'app
    """
    return state.config


@app.post("/config")
async def update_config(payload: dict):
    """
    Met à jour la configuration de l'app
    """
    state.config.update(payload)
    return {"status": "ok", "config": state.config}


@app.get("/layout")
async def get_layout():
    """
    Renvoie le layout de l'app
    """
    return state.layout


@app.post("/layout")
async def update_layout(payload: dict):
    """
    Met à jour la disposition des widgets
    """
    state.layout = payload
    return {"status": "ok"}


@app.get("/layout/presets")
async def get_layout_presets():
    """
    Liste tous les presets de disposition disponibles
    """
    return {
        pid: {"label": p["label"], "description": p["description"]}
        for pid, p in LAYOUT_PRESETS.items()
    }


######################################################################
################################# UI #################################
######################################################################

@app.get("/", response_class=HTMLResponse)
async def management_ui():
    """
    Renvoie l'écran de gestion d'affichaage
    """
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)