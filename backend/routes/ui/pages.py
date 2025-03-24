from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import time
import os
import platform

from config import config
from backend.modules.smartcard_manager import SmartcardManager
from backend.modules.nfc_manager import NFCManager
from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors

# Create logger and router
logger = get_api_logger()
router = APIRouter()

# Set up templates
templates = Jinja2Templates(directory=config.TEMPLATE_DIR)

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    """Serve the splash page."""
    try:
        splash_path = os.path.join(os.path.dirname(__file__), "splash.html")
        with open(splash_path, "r") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error loading splash page: {e}")
        return HTMLResponse(content=f"""
        <html>
            <body style="font-family: Arial; background: #07182E; color: white; padding: 20px;">
                <h1>Error loading splash page</h1>
                <p>Could not find splash.html. Error: {e}</p>
                <p>Path: {splash_path}</p>
                <p><a href="/dashboard" style="color: #00b7ff;">Go to Dashboard</a> |
                   <a href="/api/docs" style="color: #00b7ff;">API Documentation</a></p>
            </body>
        </html>
        """)

# Define route for dashboard (previously this was probably at the root URL)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/smartcard", response_class=HTMLResponse)
@handle_errors
async def smartcard(request: Request):
    """Render the smartcard operations page."""
    return templates.TemplateResponse("smartcard.html", {"request": request})

@router.get("/mifare", response_class=HTMLResponse)
@handle_errors
async def mifare(request: Request):
    """Render the mifare operations page."""
    return templates.TemplateResponse("mifare.html", {"request": request})

@router.get("/nfc", response_class=HTMLResponse)
@handle_errors
async def nfc(request: Request):
    """Render the nfc operations page."""
    return templates.TemplateResponse("nfc.html", {"request": request})

@router.get("/settings", response_class=HTMLResponse)
@handle_errors
async def settings(request: Request):
    """Render the settings page."""
    return templates.TemplateResponse("settings.html", {"request": request})

@router.get("/biometric-fusion", response_class=HTMLResponse)
@handle_errors
async def biometric_fusion(request: Request):
    """Render the biometric fusion page."""
    return templates.TemplateResponse("biometric_fusion.html", {"request": request})

@router.get("/uwb", response_class=HTMLResponse)
@handle_errors
async def uwb(request: Request):
    """Render the UWB manager page."""
    return templates.TemplateResponse("uwb.html", {"request": request})

@router.get("/palm-recognition", response_class=HTMLResponse)
@handle_errors
async def palm_recognition(request: Request):
    """Render the palm recognition page."""
    return templates.TemplateResponse("palm_recognition.html", {"request": request})

@router.get("/mqtt", response_class=HTMLResponse)
@handle_errors
async def mqtt(request: Request):
    """Render the MQTT manager page."""
    return templates.TemplateResponse("mqtt.html", {"request": request})

@router.get("/iris-recognition", response_class=HTMLResponse)
@handle_errors
async def iris_recognition(request: Request):
    """Render the iris recognition page."""
    return templates.TemplateResponse("iris_recognition.html", {"request": request})

@router.get("/fingerprint", response_class=HTMLResponse)
@handle_errors
async def fingerprint(request: Request):
    """Render the fingerprint manager page."""
    return templates.TemplateResponse("fingerprint.html", {"request": request})

@router.get("/facial-recognition", response_class=HTMLResponse)
@handle_errors
async def facial_recognition(request: Request):
    """Render the facial recognition page."""
    return templates.TemplateResponse("facial_recognition.html", {"request": request})

@router.get("/device-manager", response_class=HTMLResponse)
@handle_errors
async def device_manager(request: Request):
    """Render the device manager page."""
    return templates.TemplateResponse("device_manager.html", {"request": request})

@router.get("/card-manager", response_class=HTMLResponse)
@handle_errors
async def card_manager(request: Request):
    """Render the card manager page."""
    return templates.TemplateResponse("card_manager.html", {"request": request})

@router.get("/ble", response_class=HTMLResponse)
@handle_errors
async def ble(request: Request):
    """Render the BLE manager page."""
    return templates.TemplateResponse("ble.html", {"request": request})

@router.get("/biometric-manager", response_class=HTMLResponse)
@handle_errors
async def biometric_manager(request: Request):
    """Render the biometric manager page."""
    return templates.TemplateResponse("biometric_manager.html", {"request": request})

for route in router.routes:
    print(f"Registered UI route: {route.path}")