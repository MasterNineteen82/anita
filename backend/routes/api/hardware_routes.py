from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
from backend.hardware.hardware_interface import HardwareInterface
from backend.modules.system_manager import SystemManager
from backend.models import StatusResponse, ErrorResponse, LogRequest, Settings
from ..utils import handle_errors, validate_json

logger = logging.getLogger(__name__)
router = APIRouter(tags=["hardware"])

class HardwareCommandRequest(BaseModel):
    device: str
    command: str
    parameters: Optional[Dict[str, Any]] = None

@router.get("/hardware/list", summary="List connected hardware devices")
@handle_errors
async def list_hardware():
    """List all connected hardware devices"""
    hardware = HardwareInterface()
    devices = hardware.list_devices()
    
    return {
        "status": "success",
        "data": {
            "devices": devices
        }
    }

@router.get("/hardware/status", summary="Get hardware status")
@handle_errors
async def get_hardware_status():
    """Get status of all hardware components"""
    hardware = HardwareInterface()
    status = hardware.get_status()
    
    return {
        "status": "success",
        "data": status
    }

@router.post("/hardware/command", summary="Send command to hardware device")
@handle_errors
async def send_hardware_command(request: HardwareCommandRequest):
    """Send a command to a hardware device"""
    hardware = HardwareInterface()
    result = hardware.send_command(
        device=request.device,
        command=request.command,
        parameters=request.parameters
    )
    
    return {
        "status": "success",
        "data": result
    }

@router.get("/hardware/diag", summary="Run hardware diagnostics")
@handle_errors
async def run_hardware_diagnostics():
    """Run diagnostics on hardware components"""
    hardware = HardwareInterface()
    diag_results = hardware.run_diagnostics()
    
    return {
        "status": "success",
        "data": diag_results
    }