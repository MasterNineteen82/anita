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
# Remove direct import of ble_routes here
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

# Mount static files
base_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "frontend", "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=os.path.join(base_dir, "frontend", "templates"))

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

# Setup monitoring
setup_monitoring(app)

# Modify the startup event to check if the BLE router is already registered
@app.on_event("startup")
async def startup_event():
    # Only initialize BLE module if not already initialized in app.py
    if not any(route.path.startswith("/api/ble") for route in app.routes if hasattr(route, "path")):
        try:
            # Import BLE components only at startup time
            from backend.routes.api import ble_routes
            from backend.modules.ble.api.ble_routes import router as ble_router
            
            # Register BLE router with proper error handling
            app.include_router(
                ble_router, 
                prefix="/api" if not ble_router.prefix else "", 
                tags=["BLE"]
            )
            
            logger.info("BLE module initialized successfully")
            
        except Exception as ble_error:
            logger.error(f"Failed to initialize BLE module: {ble_error}", exc_info=True)
            logger.warning("Application will continue without BLE functionality")

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
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ble", response_class=HTMLResponse)
async def ble_page(request: Request):
    return templates.TemplateResponse("ble.html", {"request": request})

# Add other frontend routes as needed (e.g., /smartcard, /nfc, etc.)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)