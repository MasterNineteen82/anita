import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
import sys
import uvicorn
from ws.manager import manager
from backend.modules.monitoring import setup_monitoring
from modules.uwb_manager import setup_uwb_monitoring
from backend.routes import (
    auth_router, biometric_router, ble_router, cache_router, card_router,
    device_router, hardware_router, mifare_router, mqtt_router, nfc_router,
    rfid_router, security_router, smartcard_router, system_router, uwb_router,
    get_monitoring_router  # Import the getter
)
from backend.ws.manager import manager, WebSocketHandler
# from modules.uwb.handlers import register_uwb_handlers
from .routes import device_routes

# Import your route modules
from backend.routes.api.uwb_routes import router as uwb_router
from backend.routes.api.system_routes import router as system_router
# Import other routers...

# System path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ANITA Backend",
    description="API for managing various device interfaces",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# List of known routers
known_routers = [
    auth_router,
    biometric_router,
    ble_router,
    cache_router,
    card_router,
    device_router,
    hardware_router,
    mifare_router,
    mqtt_router,
    nfc_router,
    rfid_router,
    security_router,
    smartcard_router,
    system_router,
    uwb_router,
    get_monitoring_router(),  # Call the getter to get the router object
]

# Include routers with appropriate prefixes
app.include_router(system_router, tags=["System"])
app.include_router(uwb_router, prefix="/api", tags=["UWB"])
app.include_router(device_routes.router)
app.include_router(ble_router.router)

# Set up BLE monitoring
ble_router.setup_ble_monitoring(app)

# Set up monitoring systems
@app.on_event("startup")
async def startup_event():
    # Set up system monitoring
    setup_monitoring(app)
    
    # Set up UWB monitoring
    await setup_uwb_monitoring()
    
    # Register handlers
    # register_uwb_handlers()
    
    logger.info("Application startup complete")

# UWB WebSocket endpoint
@app.websocket("/ws/uwb")
async def uwb_websocket(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    
    try:
        # Join UWB room
        await manager.join_room(websocket, "uwb")
        logger.info(f"Client {client_id} connected to UWB WebSocket")
        
        # Handle incoming messages
        async for message in websocket.iter_json():
            await manager.handle_message(websocket, message)
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from UWB WebSocket")
    except Exception as e:
        logger.error(f"Error in UWB WebSocket: {str(e)}")
    finally:
        # Always disconnect properly
        await manager.disconnect(websocket)

# Root route
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content="<h1>Device Management API</h1><p>API documentation available at <a href='/docs'>/docs</a></p>")

# Add shutdown event to clean up resources
@app.on_event("shutdown")
async def shutdown_event():
    from .modules.device_manager import DeviceManager
    DeviceManager.shutdown_executor()

# Run the application
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)