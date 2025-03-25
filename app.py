from fastapi import FastAPI, Request, HTTPException, Query
from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import uvicorn
from typing import Optional
from datetime import datetime
import glob


# Add the project root to sys.path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import routers
from backend.modules.monitors import setup_monitoring, monitoring_manager
from backend.routes.api import device_routes, smartcard_routes, nfc_routes, mifare_routes, biometric_routes
from backend.routes.api import card_routes, system_routes, uwb_routes, auth_routes, ble_routes
from backend.routes.api import cache_routes, hardware_routes, mqtt_routes, rfid_routes, security_routes
from backend.routes.api.monitoring_router import router as monitoring_router
from backend.logging.logging_config import setup_logging, print_colorful_traceback
import importlib
import pkgutil
import inspect
from backend.routes import api as api_package

# Set up logging
logger = setup_logging()

# Initialize FastAPI application
app = FastAPI(
    title="ANITA POC",
    description="Advanced NFC/IoT Technology Application",
    version="0.1.0"
)

# Set up monitoring system
setup_monitoring(app)

# Mount static files from the frontend directory
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# API Router Instance
frontend_router = APIRouter()

# Update template directory to use absolute path
# Get the directory where app.py is located
base_dir = os.path.dirname(os.path.abspath(__file__))
# Set the template directory to an absolute path
template_dir = os.path.join(base_dir, "frontend", "templates")
templates = Jinja2Templates(directory=template_dir)

# Log the template directory for debugging
logger.info(f"Using template directory: {template_dir}")

# Log configuration
LOG_DIR = os.environ.get('LOG_DIR', 'poc/logging')
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

@app.on_event("startup")
async def start_ble_monitor():
    await monitoring_manager.start_monitor("ble_device_monitor", room_name="ble_notifications")

# Helper functions for log handling
def get_available_logs():
    """Get all available log files from the log directory"""
    log_files = []
    
    # Get all files from errors subdirectory
    errors_dir = os.path.join(LOG_DIR, 'errors')
    if os.path.exists(errors_dir):
        for file_path in glob.glob(f"{errors_dir}/*.log*"):
            file_name = os.path.basename(file_path)
            log_files.append(os.path.join('errors', file_name))
    
    # Get all files from main log directory
    if os.path.exists(LOG_DIR):
        for file_path in glob.glob(f"{LOG_DIR}/*.log*"):
            file_name = os.path.basename(file_path)
            log_files.append(file_name)
    
    return sorted(log_files)

def parse_log_level(line):
    """Extract log level from a log line"""
    for level in LOG_LEVELS:
        if f" {level} " in line:
            return level
    return None

def filter_logs(log_file, min_level=None, max_lines=100):
    """Read and filter logs from a file based on minimum level"""
    log_path = os.path.join(LOG_DIR, log_file)
    
    if not os.path.exists(log_path):
        return []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Error reading log file {log_path}: {e}")
        return []
    
    # Filter by log level if specified
    if min_level and min_level in LOG_LEVELS:
        min_level_index = LOG_LEVELS.index(min_level)
        filtered_lines = []
        for line in lines:
            level = parse_log_level(line)
            if level and LOG_LEVELS.index(level) >= min_level_index:
                filtered_lines.append(line)
        lines = filtered_lines
    
    # Return the last N lines
    return lines[-int(max_lines):]

# Debug: Print all routes at startup
@app.on_event("startup")
async def startup_event():
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", ["GET"])
            routes.append(f"{route.path} [{', '.join(methods)}]")
    routes.sort()
    logger.info("Available routes:")
    for route in routes:
        logger.info(f"  {route}")


# API Explorer routes
@app.get("/api_explorer", response_class=HTMLResponse)
async def api_explorer(request: Request):
    """Render the API Explorer interface"""
    return templates.TemplateResponse("api_explorer.html", {"request": request})

# Endpoint to get API documentation in JSON format for the explorer
@app.get("/api/docs.json")
async def api_docs():
    """Return structured API documentation in JSON format"""
    routes_info = []
    for route in app.routes:
        if hasattr(route, "path") and "/api/" in route.path and not route.path.endswith("docs.json"):
            # Extract endpoint information
            path = route.path
            methods = list(route.methods) if hasattr(route, "methods") else ["GET"]
            
            # Try to get function docstring for description
            description = ""
            if hasattr(route, "endpoint") and route.endpoint.__doc__:
                description = route.endpoint.__doc__.strip()
            
            # Try to get tags from route
            tags = []
            if hasattr(route, "tags"):
                tags = route.tags
            elif "smartcard" in path:
                tags = ["Smartcard"]
            elif "nfc" in path:
                tags = ["NFC"]
            elif "mifare" in path:
                tags = ["MIFARE"]
            elif "biometric" in path:
                tags = ["Biometric"]
            elif "card" in path and "smartcard" not in path:
                tags = ["Card"]
            elif "system" in path:
                tags = ["System"]
            elif "uwb" in path:
                tags = ["UWB"]
            elif "log" in path:
                tags = ["Logs"]
            else:
                tags = ["Miscellaneous"]
            
            # Add route info
            for method in methods:
                routes_info.append({
                    "path": path,
                    "method": method,
                    "description": description,
                    "tags": tags,
                    "summary": description.split("\n")[0] if description else f"{method} {path}"
                })
    
    # Get statistics
    routes_count = len(routes_info)
    
    # Group by tags
    categorized_routes = {}
    for route in routes_info:
        for tag in route["tags"]:
            if tag not in categorized_routes:
                categorized_routes[tag] = []
            categorized_routes[tag].append(route)
    
    return {
        "routes": routes_info,
        "routes_count": routes_count,
        "categorized_routes": categorized_routes
    }

# Dynamic route discovery for backend modules

# Dictionary of known routers to ensure we don't miss anything
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
    "ble_routes": ble_routes.router,
    "cache_routes": cache_routes.router,
    "hardware_routes": hardware_routes.router,
    "mqtt_routes": mqtt_routes.router,
    "rfid_routes": rfid_routes.router,
    "security_routes": security_routes.router,
    "monitoring_router": monitoring_router
}


# Dynamically discover additional routers in the api package
for _, name, _ in pkgutil.iter_modules(api_package.__path__, api_package.__name__ + "."):
    try:
        module = importlib.import_module(name)
        for item_name, item in inspect.getmembers(module):
            # Check if it's a router that's not already in our known_routers
            if item_name == "router" and hasattr(item, "routes") and name.split(".")[-1] + "_routes" not in known_routers:
                router_name = name.split(".")[-1] + "_routes"
                known_routers[router_name] = item
                logger.info(f"Dynamically discovered router: {router_name}")
    except Exception as e:
        logger.error(f"Error importing module {name}: {e}")

# Include all routers
for router_name, router in known_routers.items():
    logger.info(f"Including router: {router_name}")
    try:
        # Check if router already has a prefix
        if not getattr(router, "prefix", "") or router.prefix == "":
            # Only add /api prefix if it doesn't already have one
            app.include_router(router, prefix="/api")
        else:
            # If it already has a prefix, include it as-is
            app.include_router(router)
        logger.info(f"Successfully included router: {router_name}")
    except Exception as e:
        logger.error(f"Error including router {router_name}: {e}")
        
# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.info("Root endpoint accessed")
    return templates.TemplateResponse("index.html", {"request": request})

# Logs page
@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    log_files = get_available_logs()
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "log_files": log_files,
        "log_levels": LOG_LEVELS
    })

# API endpoint to get logs
@app.get("/api/logs")
async def get_logs(
    log_file: str = Query(..., description="Log file to retrieve"),
    log_level: Optional[str] = Query("INFO", description="Minimum log level to show"),
    log_lines: int = Query(100, description="Maximum number of lines to return")
):
    if not log_file:
        raise HTTPException(status_code=400, detail="Log file not specified")
    
    logs = filter_logs(log_file, log_level, log_lines)
    return {
        "logs": logs,
        "count": len(logs),
        "file": log_file,
        "level": log_level
    }

# API endpoint to list available logs
@app.get("/api/available_logs")
async def available_logs():
    log_files = get_available_logs()
    return {
        "log_files": log_files,
        "count": len(log_files)
    }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }

# Help page
@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})

# Config page
@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse("config.html", {"request": request})

# API documentation page
@app.get("/docs-custom", response_class=HTMLResponse)
async def api_docs_page(request: Request):
    return templates.TemplateResponse("api_explorer.html", {"request": request})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    print_colorful_traceback(sys.exc_info())
    if "TemplateNotFound" in str(exc) or "jinja2" in str(exc).lower():
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "error": f"Template Error: {str(exc)}"},
            status_code=500
        )
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"Internal server error: {str(exc)}"}
    )

# Handle 404 errors
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "error": "404 - Page Not Found"},
        status_code=404
    )

@app.get("/debug-templates")
async def debug_templates():
    template_dir = os.path.abspath("frontend/templates")
    template_files = os.listdir(template_dir) if os.path.exists(template_dir) else []
    return {
        "template_dir": template_dir,
        "exists": os.path.exists(template_dir),
        "templates": template_files,
        "working_dir": os.getcwd()
    }

# Add this to app.py temporarily for debugging
@app.get("/debug-static")
async def debug_static():
    static_dir = os.path.join(base_dir, "frontend", "static")
    js_dir = os.path.join(static_dir, "js", "pages")
    return {
        "static_dir": static_dir,
        "static_exists": os.path.exists(static_dir),
        "js_dir": js_dir,
        "js_dir_exists": os.path.exists(js_dir),
        "ble_js_path": os.path.join(js_dir, "ble.js"),
        "ble_js_exists": os.path.exists(os.path.join(js_dir, "ble.js")),
        "files_in_js_dir": os.listdir(js_dir) if os.path.exists(js_dir) else []
    }

# Frontend routes
@app.get("/smartcard", response_class=HTMLResponse)
async def smartcard_page(request: Request):
    return templates.TemplateResponse("smartcard.html", {"request": request})

@app.get("/nfc", response_class=HTMLResponse)
async def nfc_page(request: Request):
    return templates.TemplateResponse("nfc.html", {"request": request})

@app.get("/mifare", response_class=HTMLResponse)
async def mifare_page(request: Request):
    return templates.TemplateResponse("mifare.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/biometric_fusion", response_class=HTMLResponse)
async def biometric_fusion_page(request: Request):
    return templates.TemplateResponse("biometric_fusion.html", {"request": request})

@app.get("/biometric_manager", response_class=HTMLResponse)
async def biometric_manager_page(request: Request):
    return templates.TemplateResponse("biometric_manager.html", {"request": request})

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

# API Manager - Frontend
@app.get("/api_manager", response_class=HTMLResponse)
async def api_manager_page(request: Request):
    return templates.TemplateResponse("api_manager.html", {"request": request})

# Websocket Manager - Frontend
@app.get("/websocket_manager", response_class=HTMLResponse)
async def websocket_manager(request: Request):
    return templates.TemplateResponse("websocket_manager.html", {"request": request})


# Modal Pages (usually rendered via AJAX or fetch)
@app.get("/modals/nfc-vcard-modal", response_class=HTMLResponse)
async def nfc_vcard_modal(request: Request):
    return templates.TemplateResponse("modals/nfc-vcard-modal.html", {"request": request})

@app.get("/modals/nfc-wifi-modal", response_class=HTMLResponse)
async def nfc_wifi_modal(request: Request):
    return templates.TemplateResponse("modals/nfc-wifi-modal.html", {"request": request})

@app.get("/modals/nfc-write-text-modal", response_class=HTMLResponse)
async def nfc_write_text_modal(request: Request):
    return templates.TemplateResponse("modals/nfc-write-text-modal.html", {"request": request})

@app.get("/modals/nfc-write-url-modal", response_class=HTMLResponse)
async def nfc_write_url_modal(request: Request):
    return templates.TemplateResponse("modals/nfc-write-url-modal.html", {"request": request})


# Run the application
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
