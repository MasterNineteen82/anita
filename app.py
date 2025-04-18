from fastapi import FastAPI, Request, HTTPException, Query, WebSocket
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import uvicorn
from typing import Optional
from datetime import datetime
import glob
import asyncio
import sys
import pkgutil
import importlib
import inspect
from contextlib import asynccontextmanager
from starlette.routing import Mount
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ws.factory import websocket_factory
from backend.modules.monitors import monitoring_manager
from backend.routes.api import (
    device_routes, smartcard_routes, nfc_routes, mifare_routes, biometric_routes,
    card_routes, system_routes, uwb_routes, auth_routes, cache_routes,
    hardware_routes, mqtt_routes, rfid_routes, security_routes, monitoring_router
)
from backend.modules.ble import ble_routes
from backend.logging.logging_config import setup_logging, print_colorful_traceback
from backend.routes import api as api_package

# Import the WebSocket endpoint directly
from backend.modules.ble.comms.websocket import websocket_endpoint

# Import existing BLE routers
from backend.modules.ble.api import adapter_routes as ble_adapter_routes 
from backend.modules.ble.api import device_routes as ble_device_routes   
from backend.modules.ble.api import ble_routes as ble_router

# Import WebSocket modules and factory
from backend.ws.factory import websocket_factory
from backend.ws import ble_socket, uwb_socket, biometric_socket, card_socket, mqtt_socket

# Add import for the route mapper (to be created) - Keeping this for now
from backend.modules.ble.api.route_mapper import frontend_api_router

logger = setup_logging()

app = FastAPI(
    title="ANITA Backend",
    description="Advanced NFC/IoT Technology Application",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the WebSocket factory router for all WebSocket endpoints
app.include_router(websocket_factory.router)

base_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "frontend", "static")), name="static")

template_dir = os.path.join(base_dir, "frontend", "templates")
templates = Jinja2Templates(directory=template_dir)
logger.info(f"Using template directory: {template_dir}")

LOG_DIR = os.environ.get('LOG_DIR', 'poc/logging')
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# Map the frontend-facing BLE WebSocket endpoint
@app.websocket("/api/ble/ws/ble")
async def ble_websocket_frontend(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Keep the original WebSocket endpoint for backward compatibility
@app.websocket("/api/ws/ble")
async def ble_websocket(websocket: WebSocket):
    # Import function directly rather than trying to access it from the router
    from backend.modules.ble.comms.websocket import websocket_endpoint
    await websocket_endpoint(websocket)

# Add this new endpoint that matches the path our JS client expects
@app.websocket("/api/ble/ws")
async def ble_websocket_main(websocket: WebSocket):
    """Primary WebSocket endpoint for BLE notifications"""
    # Import the websocket handler from our new notification module
    from backend.modules.ble.comms.websocket import websocket_endpoint
    await websocket_endpoint(websocket)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    routes = [
        f"{route.path} [{' '.join(route.methods)}]"
        for route in app.routes
        if not isinstance(route, Mount) and hasattr(route, "methods")
    ]
    routes.sort()
    logger.info("Available routes:")
    for route in routes:
        logger.info(f"  {route}")
    logger.info("Application startup complete")
    await monitoring_manager.start_all()
    yield
    # Shutdown
    logger.info("Shutting down monitoring system")
    await monitoring_manager.stop_all()
    logger.info("Application shutdown complete")

app.lifespan = lifespan

@app.get("/health", tags=["System"])
async def health_check():
    """Check the health of the application."""
    return {"status": "healthy"}

# Explicitly include known routers
known_routers = {
    "smartcard_routes": smartcard_routes.router,
    "nfc_routes": nfc_routes.router,
    "mifare_routes": mifare_routes.router,
    "biometric_routes": biometric_routes.router,
    "card_routes": card_routes.router,
    "system_routes": system_routes.router,
    "uwb_routes": uwb_routes.router,
    "device_routes": device_routes.router,
    "auth_routes": auth_routes.router,
    "cache_routes": cache_routes.router,
    "hardware_routes": hardware_routes.router,
    "mqtt_routes": mqtt_routes.router,
    "rfid_routes": rfid_routes.router,
    "security_routes": security_routes.router,
    "monitoring_router": monitoring_router.router,
    "ble_routes": ble_routes.routes
}

# Update the router registration section:

# Get BLE router
try:
    has_ble_device_router = True
    has_ble_adapter_router = True
except ImportError:
    has_ble_device_router = False
    has_ble_adapter_router = False
    logger.warning("BLE module routers could not be imported")

# Try importing frontend_api_router
try:
    from backend.modules.ble.api.route_mapper import frontend_api_router
    has_frontend_api = True
except ImportError:
    has_frontend_api = False
    logger.warning("BLE frontend API router could not be imported")

# Include API router
try:
    app.include_router(api_package.router, prefix="/api")
    logger.info("Main API router registered successfully")
except AttributeError:
    logger.error("Main API router not found - check backend/routes/api/__init__.py")

# Include frontend API router if available
if has_frontend_api:
    try:
        app.include_router(frontend_api_router)
        logger.info("BLE frontend API router registered successfully")
    except Exception as e:
        logger.error(f"Failed to register BLE frontend API router: {e}")

# Include BLE device router if available
if has_ble_device_router:
    try:
        app.include_router(ble_device_routes.device_router, prefix="/api/ble", tags=["BLE Device"])
        logger.info("BLE device routes registered successfully")
    except Exception as e:
        logger.error(f"Failed to register BLE device routes: {e}")

# Include BLE adapter router if available
if has_ble_adapter_router:
    try:
        app.include_router(ble_adapter_routes.adapter_router, prefix="/api/ble", tags=["BLE Adapter"])
        logger.info("BLE adapter routes registered successfully")
    except Exception as e:
        logger.error(f"Failed to register BLE adapter routes: {e}")

# Include BLE router if available
try:
    app.include_router(ble_routes, prefix="/api")
    logger.info("BLE routes registered successfully")
except Exception as e:
    logger.error(f"Failed to register BLE routes: {e}")

# Include other routers -- COMMENTED OUT AS api_package.router SHOULD HANDLE THESE
# for router_name, router in known_routers.items():
#     # Skip BLE router since we already included it
#     if router_name == "ble_routes":
#         continue
        
#     logger.info(f"Including router: {router_name}")
#     try:
#         app.include_router(router, prefix="/api" if not getattr(router, "prefix", "") else "")
#         logger.info(f"Successfully included router: {router_name}")
#     except Exception as e:
#         logger.error(f"Error including router {router_name}: {e}")

# Dynamic router discovery - COMMENTED OUT DUE TO POTENTIAL DUPLICATES
# routes_dir = os.path.join(base_dir, "backend", "routes", "api")
# for _, name, _ in pkgutil.iter_modules([routes_dir]):
#     module_name = f"backend.routes.api.{name}"
#     try:
#         module = importlib.import_module(module_name)
#         # Check if the module has a 'router' attribute
#         if hasattr(module, "router"):
#             # Avoid re-including routers already in known_routers or handled explicitly
#             if name not in known_routers and module.router not in [ble_router, frontend_api_router, api_package.router]:
#                 app.include_router(module.router, prefix="/api", tags=[name.replace("_routes", "").capitalize()])
#                 logger.info(f"Dynamically included router: {name}")
#     except Exception as e:
#         logger.error(f"Error dynamically discovering/including router {module_name}: {e}")

def get_available_logs():
    log_files = []
    errors_dir = os.path.join(LOG_DIR, 'errors')
    if os.path.exists(errors_dir):
        for file_path in glob.glob(f"{errors_dir}/*.log*"):
            log_files.append(os.path.join('errors', os.path.basename(file_path)))
    if os.path.exists(LOG_DIR):
        for file_path in glob.glob(f"{LOG_DIR}/*.log*"):
            log_files.append(os.path.basename(file_path))
    return sorted(log_files)

def parse_log_level(line):
    for level in LOG_LEVELS:
        if f" {level} " in line:
            return level
    return None

def filter_logs(log_file, min_level=None, max_lines=100):
    log_path = os.path.join(LOG_DIR, log_file)
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Error reading log file {log_path}: {e}")
        return []
    if min_level and min_level in LOG_LEVELS:
        min_level_index = LOG_LEVELS.index(min_level)
        filtered_lines = [line for line in lines if parse_log_level(line) and LOG_LEVELS.index(parse_log_level(line)) >= min_level_index]
        lines = filtered_lines
    return lines[-int(max_lines):]

# API Explorer routes
@app.get("/api_explorer", response_class=HTMLResponse)
async def api_explorer(request: Request):
    return templates.TemplateResponse("api_explorer.html", {"request": request})

@app.get("/api/docs.json")
async def api_docs():
    routes_info = []
    for route in app.routes:
        if hasattr(route, "path") and "/api/" in route.path and not route.path.endswith("docs.json"):
            methods = list(route.methods) if hasattr(route, "methods") else ["GET"]
            description = route.endpoint.__doc__.strip() if hasattr(route, "endpoint") and route.endpoint.__doc__ else ""
            tags = getattr(route, "tags", ["Miscellaneous"])
            for method in methods:
                routes_info.append({
                    "path": route.path,
                    "method": method,
                    "description": description,
                    "tags": tags,
                    "summary": description.split("\n")[0] if description else f"{method} {route.path}"
                })
    routes_count = len(routes_info)
    categorized_routes = {}
    for route in routes_info:
        for tag in route["tags"]:
            categorized_routes.setdefault(tag, []).append(route)
    return {"routes": routes_info, "routes_count": routes_count, "categorized_routes": categorized_routes}

# Add BLE test page
@app.get("/ble_test", response_class=HTMLResponse)
async def ble_test(request: Request):
    """BLE Test Interface for direct API testing"""
    return templates.TemplateResponse("ble_test.html", {"request": request})

# Frontend routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.info("Root endpoint accessed")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    log_files = get_available_logs()
    return templates.TemplateResponse("logs.html", {"request": request, "log_files": log_files, "log_levels": LOG_LEVELS})

@app.get("/logs/get", response_class=JSONResponse)
async def get_logs(log_file: str = Query(...), log_level: Optional[str] = Query("INFO"), log_lines: int = Query(100)):
    return filter_logs(log_file, log_level, log_lines)

@app.get("/logs/available", response_class=JSONResponse)
async def available_logs():
    return get_available_logs()

@app.get("/health", response_class=JSONResponse)
async def health_check():
    return {"status": "ok"}

@app.get("/ble", response_class=HTMLResponse)
async def ble_page(request: Request):
    return templates.TemplateResponse("ble.html", {"request": request})

@app.get("/card_manager", response_class=HTMLResponse)
async def card_manager_page(request: Request):
    return templates.TemplateResponse("card_manager.html", {"request": request})

@app.get("/device_manager", response_class=HTMLResponse)
async def device_manager_page(request: Request):
    return templates.TemplateResponse("device_manager.html", {"request": request})

@app.get("/facial_recognition", response_class=HTMLResponse)
async def facial_recognition_page(request: Request):
    return templates.TemplateResponse("facial_recognition.html", {"request": request})

@app.get("/fingerprint", response_class=HTMLResponse)
async def fingerprint_page(request: Request):
    return templates.TemplateResponse("fingerprint.html", {"request": request})

@app.get("/iris_recognition", response_class=HTMLResponse)
async def iris_recognition_page(request: Request):
    return templates.TemplateResponse("iris_recognition.html", {"request": request})

@app.get("/mqtt", response_class=HTMLResponse)
async def mqtt_page(request: Request):
    return templates.TemplateResponse("mqtt.html", {"request": request})

@app.get("/rfid", response_class=HTMLResponse)
async def rfid_page(request: Request):
    return templates.TemplateResponse("rfid.html", {"request": request})

@app.get("/splash", response_class=HTMLResponse)
async def splash_page(request: Request):
    return templates.TemplateResponse("splash.html", {"request": request})

@app.get("/uwb", response_class=HTMLResponse)
async def uwb_page(request: Request):
    return templates.TemplateResponse("uwb.html", {"request": request})

@app.get("/api_manager", response_class=HTMLResponse)
async def api_manager_page(request: Request):
    return templates.TemplateResponse("api_manager.html", {"request": request})

@app.get("/websocket_manager", response_class=HTMLResponse)
async def websocket_manager(request: Request):
    return templates.TemplateResponse("websocket_manager.html", {"request": request})

@app.get("/ble/dashboard", response_class=HTMLResponse)
async def ble_dashboard(request: Request):
    """Render the BLE dashboard page"""
    return templates.TemplateResponse("ble_dashboard.html", {"request": request})

@app.get("/ble/logging", response_class=HTMLResponse)
async def ble_logging_page(request: Request):
    """Render the BLE Logging Dashboard page"""
    return templates.TemplateResponse("ble_logging.html", {"request": request})

@app.get("/palm_recognition", response_class=HTMLResponse)
async def palm_recognition_page(request: Request):
    return templates.TemplateResponse("palm_recognition.html", {"request": request})

@app.get("/smartcard", response_class=HTMLResponse)
async def smartcard_page(request: Request):
    return templates.TemplateResponse("smartcard.html", {"request": request})

@app.get("/nfc", response_class=HTMLResponse)
async def nfc_page(request: Request):
    return templates.TemplateResponse("nfc.html", {"request": request})

@app.get("/mifare", response_class=HTMLResponse)
async def mifare_page(request: Request):
    return templates.TemplateResponse("mifare.html", {"request": request})

@app.get("/biometric_manager", response_class=HTMLResponse)
async def biometric_manager_page(request: Request):
    return templates.TemplateResponse("biometric_manager.html", {"request": request})

@app.get("/biometric_fusion", response_class=HTMLResponse)
async def biometric_fusion_page(request: Request):
    return templates.TemplateResponse("biometric_fusion.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})

# Modal Pages
@app.get("/modals/nfc/vcard", response_class=HTMLResponse)
async def nfc_vcard_modal(request: Request):
    return templates.TemplateResponse("modals/nfc_vcard.html", {"request": request})

@app.get("/modals/nfc/wifi", response_class=HTMLResponse)
async def nfc_wifi_modal(request: Request):
    return templates.TemplateResponse("modals/nfc_wifi.html", {"request": request})

@app.get("/modals/nfc/write_text", response_class=HTMLResponse)
async def nfc_write_text_modal(request: Request):
    return templates.TemplateResponse("modals/nfc_write_text.html", {"request": request})

@app.get("/modals/nfc/write_url", response_class=HTMLResponse)
async def nfc_write_url_modal(request: Request):
    return templates.TemplateResponse("modals/nfc_write_url.html", {"request": request})

# Catch-all route for undefined paths to prevent 404 errors
@app.get("/{path:path}", response_class=HTMLResponse)
async def catch_all(request: Request, path: str):
    logger.warning(f"Undefined route accessed: /{path}")
    return templates.TemplateResponse("error.html", {"request": request, "error_code": 404, "error_message": f"The page '/{path}' was not found."})

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    print_colorful_traceback(sys.exc_info())
    if "TemplateNotFound" in str(exc):
        return templates.TemplateResponse("error.html", {"request": request, "error": f"Template Error: {str(exc)}"}, status_code=500)
    return JSONResponse(status_code=500, content={"status": "error", "message": f"Internal server error: {str(exc)}"})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return templates.TemplateResponse("error.html", {"request": request, "error": "404 - Page Not Found"}, status_code=404)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)