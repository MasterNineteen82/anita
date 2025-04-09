import asyncio
import logging
import os
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from backend.routes.api import (
    auth_routes, biometric_routes, cache_routes, card_routes, device_routes,
    hardware_routes, mifare_routes, mqtt_routes, nfc_routes, rfid_routes,
    security_routes, smartcard_routes, system_routes, uwb_routes
)
from backend.routes.api.ble import adapter_routes as ble_adapter_routes
from backend.routes.api.ble import device_routes as ble_device_routes
from backend.routes.api.monitoring_router import router as monitoring_router
from backend.logging.logging_config import setup_logging
from backend.modules.monitors import setup_monitoring, monitoring_manager
from backend.ws.manager import manager
from backend.core.exception_handlers import global_exception_handler

# Setup logging
logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="ANITA Backend",
    description="API for managing various device interfaces",
    version="1.0.0"
)
app.add_exception_handler(Exception, global_exception_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define project root directory (one level up from backend)
base_dir = os.path.dirname(os.path.abspath(__file__)) # k:\anita\poc\backend
project_root = os.path.dirname(base_dir) # k:\anita\poc

# Mount static files relative to project root
static_dir = os.path.join(project_root, "frontend", "static")
if not os.path.exists(static_dir):
    logger.warning(f"Static directory not found at {static_dir}. Frontend static files may not be served.")
    # Optionally create the directory if needed, or handle differently
    # os.makedirs(static_dir, exist_ok=True)
else:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates relative to project root
templates_dir = os.path.join(project_root, "frontend", "templates")
if not os.path.exists(templates_dir):
    logger.error(f"Templates directory not found at {templates_dir}. Cannot serve frontend.")
    # Decide how to handle this - maybe raise an error or proceed without templates?
    templates = None # Indicate templates are not available
else:
    templates = Jinja2Templates(directory=templates_dir)
    logger.info(f"Using template directory: {templates_dir}")

# --- Health Check Endpoint ---
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}

# Include non-BLE routers first
routers = {
    "auth": auth_routes.router,
    "biometric": biometric_routes.router,
    "cache": cache_routes.router,
    "card": card_routes.router,
    "device": device_routes.router,
    "hardware": hardware_routes.router,
    "mifare": mifare_routes.router,
    "mqtt": mqtt_routes.router,
    "nfc": nfc_routes.router,
    "rfid": rfid_routes.router,
    "security": security_routes.router,
    "smartcard": smartcard_routes.router,
    "system": system_routes.router,
    "uwb": uwb_routes.router,
    "monitoring": monitoring_router
}

for name, router in routers.items():
    app.include_router(router, prefix="/api" if not router.prefix else "", tags=[name.capitalize()])

# Include BLE routers directly
app.include_router(ble_adapter_routes.router, prefix="/api/ble/adapter", tags=["BLE Adapter"])
app.include_router(ble_device_routes.router, prefix="/api/ble/device", tags=["BLE Device"])
logger.info("BLE routes registered successfully")

# Setup monitoring
setup_monitoring(app)

# Modify the startup event to remove BLE initialization
@app.on_event("startup")
async def startup_event():
    # Startup logic previously here (like dynamic BLE loading) is removed
    # Add any other necessary startup logic here
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await monitoring_manager.stop_monitor("ble_device_monitor")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    logger.info("Application shutdown complete")

# Frontend routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if not templates:
        return HTMLResponse("<html><body>Templates directory not found. Cannot render page.</body></html>", status_code=500)
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/ble", response_class=HTMLResponse)
async def read_ble(request: Request):
    if not templates:
        return HTMLResponse("<html><body>Templates directory not found. Cannot render page.</body></html>", status_code=500)
    return templates.TemplateResponse(request, "ble.html", {})

# Add other frontend routes as needed (e.g., /smartcard, /nfc, etc.)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)