from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
import asyncio
from backend.modules.nfc_manager import NFCManager
from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors
from backend.models import NFCMessage, NFCTextRecord, NFCURLRecord, NFCWifiCredentials
from backend.models import ErrorResponse, SuccessResponse, StatusResponse

# Update router definition with proper prefix and tags
router = APIRouter(tags=["nfc"])
logger = get_api_logger()

class NFCWriteTextRequest(BaseModel):
    text: str
    language: Optional[str] = 'en'

class NFCWriteURIRequest(BaseModel):
    uri: str

class NFCWriteVCardRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    address: Optional[str] = None

class NFCWriteRawRequest(BaseModel):
    records: List[Dict[str, Any]]

@router.get("/nfc/status", summary="Get NFC reader status")
@handle_errors
async def get_nfc_status():
    """
    Get the status of the NFC reader.
    
    Returns:
        Dictionary containing the status of the NFC reader.
    """
    return {
        "status": "success",
        "data": {
            "available": True,
            "enabled": True,
            "device_name": "Simulated NFC Reader"
        }
    }

@router.get("/nfc/available", summary="Check if NFC reader is available")
@handle_errors
async def is_nfc_available():
    """
    Check if an NFC reader is available.
    
    Returns:
        Dictionary indicating if NFC reader is available.
    """
    # NFCManager.is_available is not async so we need to run it in an executor
    loop = asyncio.get_event_loop()
    available = await loop.run_in_executor(None, NFCManager.is_available)
    return {
        "status": "success", 
        "data": {"available": available}
    }

@router.get("/nfc/devices", summary="Get available NFC devices")
@handle_errors
async def get_nfc_devices():
    """
    Get a list of available NFC devices.
    
    Returns:
        Dictionary containing the list of NFC devices.
    """
    return {
        "status": "success", 
        "data": {"devices": ["Simulated NFC Reader"]}
    }

@router.get("/nfc/discover", summary="Discover NFC tags")
@handle_errors
async def discover_nfc_tags():
    """
    Discover NFC tags in proximity to the reader.
    
    Returns:
        Dictionary containing information about discovered tags.
    """
    return {
        "status": "success", 
        "data": {
            "tags": [{
                "device": "Simulated NFC Reader",
                "tag_info": {
                    "uid": "04:A2:B3:C4:D5",
                    "type": "MIFARE Classic 1K"
                }
            }]
        }
    }

@router.get("/nfc/read", summary="Read content from NFC tag")
@handle_errors
async def read_nfc_tag():
    """
    Read content from an NFC tag.
    
    Returns:
        Dictionary containing the data read from the tag.
    """
    # Use the static async method
    result = await NFCManager.read_tag()
    return result

@router.post("/nfc/write_text", summary="Write text to NFC tag")
@handle_errors
async def write_text_to_nfc_tag(request: NFCWriteTextRequest):
    """
    Write text to an NFC tag.
    
    Args:
        request: The text data to write to the tag.
        
    Returns:
        Dictionary indicating success or failure.
    """
    # Use the static async method
    result = await NFCManager.write_text(request.text)
    return result

@router.post("/nfc/write_uri", summary="Write URI to NFC tag")
@handle_errors
async def write_uri_to_nfc_tag(request: NFCWriteURIRequest):
    """
    Write a URI to an NFC tag.
    
    Args:
        request: The URI data to write to the tag.
        
    Returns:
        Dictionary indicating success or failure.
    """
    # This endpoint requires implementation in the NFCManager
    # For now we'll return a not implemented response
    raise HTTPException(
        status_code=501, 
        detail="URI writing is not yet implemented"
    )

@router.post("/nfc/write_vcard", summary="Write vCard to NFC tag")
@handle_errors
async def write_vcard_to_nfc_tag(request: NFCWriteVCardRequest):
    """
    Write a vCard to an NFC tag.
    
    Args:
        request: The vCard data to write to the tag.
        
    Returns:
        Dictionary indicating success or failure.
    """
    # This endpoint requires implementation in the NFCManager
    # For now we'll return a not implemented response
    raise HTTPException(
        status_code=501, 
        detail="vCard writing is not yet implemented"
    )

@router.post("/nfc/write_raw", summary="Write raw NDEF records to NFC tag") 
@handle_errors
async def write_raw_to_nfc_tag(request: NFCWriteRawRequest):
    """
    Write raw NDEF records to an NFC tag.
    
    Args:
        request: The raw NDEF records to write to the tag.
        
    Returns:
        Dictionary indicating success or failure.
    """
    # This endpoint requires implementation in the NFCManager
    # For now we'll return a not implemented response
    raise HTTPException(
        status_code=501, 
        detail="Raw NDEF writing is not yet implemented"
    )

@router.get("/nfc/emulate", summary="Emulate an NFC tag")
@handle_errors
async def emulate_nfc_tag():
    """
    Emulate an NFC tag (supported on certain devices only).
    
    Returns:
        Dictionary indicating success or failure.
    """
    # This endpoint requires implementation in the NFCManager
    # For now we'll return a not implemented response
    raise HTTPException(
        status_code=501, 
        detail="NFC tag emulation is not yet implemented"
    )

@router.get("/nfc/tag/{device_id}", summary="Check for NFC tag on specific device")
@handle_errors
async def check_nfc_tag(device_id: str):
    """
    Check if an NFC tag is present on a specific device.
    
    Args:
        device_id: The ID of the NFC device to check.
        
    Returns:
        Dictionary containing information about the detected tag.
    """
    nfc_manager = NFCManager()
    tag_info = nfc_manager.detect_tag(device_id)
    
    if tag_info:
        return {
            "status": "success", 
            "data": {"tag_present": True, "tag_info": tag_info}
        }
    else:
        return {
            "status": "success", 
            "data": {"tag_present": False}
        }