from fastapi import APIRouter, HTTPException, Request, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors

# Define router with proper prefix and tags
router = APIRouter(tags=["smartcard"])

# Get logger
logger = get_api_logger("smartcard")

# Models for smartcard operations
class APDUCommand(BaseModel):
    cla: str = Field(..., description="Class byte (2 hex chars)")
    ins: str = Field(..., description="Instruction byte (2 hex chars)")
    p1: str = Field(..., description="Parameter 1 (2 hex chars)")
    p2: str = Field(..., description="Parameter 2 (2 hex chars)")
    data: Optional[str] = Field(None, description="Command data (hex string)")
    le: Optional[int] = Field(None, description="Expected length of response")

class ReadBinaryOptions(BaseModel):
    offset: int = Field(0, description="Offset to start reading from")
    length: int = Field(256, description="Number of bytes to read")

class SmartcardSelectOptions(BaseModel):
    file_id: str = Field(..., description="File ID to select (hex string)")
    p1: str = Field("04", description="P1 parameter for SELECT")
    p2: str = Field("00", description="P2 parameter for SELECT")

# Routes for smartcard operations
@router.get("/smartcard/readers", summary="Get available smartcard readers")
@handle_errors
async def get_smartcard_readers():
    """
    Get a list of available smartcard readers connected to the system.
    
    Returns:
        Dictionary with status and list of readers.
    """
    # Mock implementation - would be replaced with actual hardware calls
    readers = [
        {
            "id": "reader1",
            "name": "ACS ACR122U USB Reader",
            "connected": True,
            "has_card": True
        },
        {
            "id": "reader2",
            "name": "HID Global OMNIKEY 5022 CL",
            "connected": True,
            "has_card": False
        }
    ]
    
    return {
        "status": "success",
        "data": readers
    }

@router.get("/smartcard/reader/{reader_id}", summary="Get smartcard reader status")
@handle_errors
async def get_smartcard_reader_status(reader_id: str):
    """
    Get status information for a specific smartcard reader.
    
    Args:
        reader_id: The ID of the reader to check.
        
    Returns:
        Dictionary with status and reader information.
    """
    # Check if reader exists
    if reader_id not in ["reader1", "reader2"]:
        raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    
    # Mock implementation - would be replaced with actual hardware calls
    has_card = reader_id == "reader1"  # Only reader1 has a card in this mock
    
    reader_status = {
        "id": reader_id,
        "name": "ACS ACR122U USB Reader" if reader_id == "reader1" else "HID Global OMNIKEY 5022 CL",
        "connected": True,
        "has_card": has_card,
        "card_protocol": "T=1" if has_card else None,
        "card_atr": "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 01 00 00 00 00 6A" if has_card else None
    }
    
    return {
        "status": "success",
        "data": reader_status
    }

@router.post("/smartcard/connect/{reader_id}", summary="Connect to smartcard")
@handle_errors
async def connect_to_smartcard(reader_id: str, protocol: Optional[str] = "T=1"):
    """
    Establish a connection to a smartcard in the specified reader.
    
    Args:
        reader_id: The ID of the reader containing the card.
        protocol: The protocol to use for communication (T=0, T=1, etc.)
        
    Returns:
        Dictionary with status and connection information.
    """
    # Check if reader exists
    if reader_id not in ["reader1", "reader2"]:
        raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    
    # Check if card is present
    if reader_id != "reader1":  # In our mock, only reader1 has a card
        raise HTTPException(status_code=400, detail="No card present in the specified reader")
    
    # Mock implementation - would be replaced with actual hardware calls
    connection_info = {
        "reader_id": reader_id,
        "protocol": protocol,
        "connected": True,
        "card_atr": "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 01 00 00 00 00 6A"
    }
    
    return {
        "status": "success",
        "message": "Connected to smartcard successfully",
        "data": connection_info
    }

@router.post("/smartcard/disconnect/{reader_id}", summary="Disconnect from smartcard")
@handle_errors
async def disconnect_from_smartcard(reader_id: str, disposition: str = "leave"):
    """
    Disconnect from a smartcard in the specified reader.
    
    Args:
        reader_id: The ID of the reader containing the card.
        disposition: What to do with the card after disconnection (leave, reset, unpower, eject).
        
    Returns:
        Dictionary with status and disconnection confirmation.
    """
    # Check if reader exists
    if reader_id not in ["reader1", "reader2"]:
        raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    
    # Validate disposition
    valid_dispositions = ["leave", "reset", "unpower", "eject"]
    if disposition not in valid_dispositions:
        raise HTTPException(status_code=400, detail=f"Invalid disposition. Must be one of: {', '.join(valid_dispositions)}")
    
    # Mock implementation - would be replaced with actual hardware calls
    return {
        "status": "success",
        "message": f"Disconnected from smartcard in reader {reader_id} with disposition '{disposition}'",
        "data": {
            "reader_id": reader_id,
            "disposition": disposition
        }
    }

@router.post("/smartcard/transmit/{reader_id}", summary="Transmit APDU command")
@handle_errors
async def transmit_apdu(reader_id: str, command: APDUCommand):
    """
    Transmit an APDU command to a smartcard.
    
    Args:
        reader_id: The ID of the reader containing the card.
        command: The APDU command to send.
        
    Returns:
        Dictionary with status and response APDU.
    """
    # Check if reader exists
    if reader_id not in ["reader1", "reader2"]:
        raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    
    # Check if card is present
    if reader_id != "reader1":  # In our mock, only reader1 has a card
        raise HTTPException(status_code=400, detail="No card present in the specified reader")
    
    # Validate APDU format
    if not (len(command.cla) == 2 and len(command.ins) == 2 and len(command.p1) == 2 and len(command.p2) == 2):
        raise HTTPException(status_code=400, detail="CLA, INS, P1, and P2 must be exactly 2 hex characters each")
    
    # Mock implementation - would be replaced with actual hardware calls
    # Generate a mock response based on the command
    if command.ins == "A4":  # SELECT
        response = "90 00"  # Success
    elif command.ins == "B0":  # READ BINARY
        response = "00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 90 00"
    elif command.ins == "D6":  # UPDATE BINARY
        response = "90 00"  # Success
    else:
        response = "6D 00"  # Instruction not supported
    
    return {
        "status": "success",
        "data": {
            "reader_id": reader_id,
            "command": f"{command.cla} {command.ins} {command.p1} {command.p2} {command.data or ''}",
            "response": response,
            "sw": response[-5:].replace(" ", "")  # Status Word (last 2 bytes)
        }
    }

@router.post("/smartcard/select/{reader_id}", summary="Select file on smartcard")
@handle_errors
async def select_smartcard_file(reader_id: str, options: SmartcardSelectOptions):
    """
    Select a file on a smartcard using the SELECT command.
    
    Args:
        reader_id: The ID of the reader containing the card.
        options: Options for the SELECT command.
        
    Returns:
        Dictionary with status and response.
    """
    # Check if reader exists
    if reader_id not in ["reader1", "reader2"]:
        raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    
    # Check if card is present
    if reader_id != "reader1":  # In our mock, only reader1 has a card
        raise HTTPException(status_code=400, detail="No card present in the specified reader")
    
    # Validate file_id format
    if len(options.file_id) % 2 != 0:
        raise HTTPException(status_code=400, detail="File ID must have an even number of characters")
    
    # Mock implementation - would be replaced with actual hardware calls
    # Create SELECT APDU: 00 A4 P1 P2 Lc Data
    command = f"00 A4 {options.p1} {options.p2} {len(options.file_id) // 2:02X} {options.file_id}"
    
    # Mock response based on file_id
    if options.file_id in ["3F00", "2F00", "2F01"]:
        response = "90 00"  # Success
    else:
        response = "6A 82"  # File not found
    
    return {
        "status": "success",
        "data": {
            "reader_id": reader_id,
            "command": command,
            "response": response,
            "sw": response[-5:].replace(" ", ""),  # Status Word (last 2 bytes)
            "file_selected": response == "90 00"
        }
    }

@router.post("/smartcard/read_binary/{reader_id}", summary="Read binary data from smartcard")
@handle_errors
async def read_binary_data(reader_id: str, options: ReadBinaryOptions):
    """
    Read binary data from the currently selected file on a smartcard.
    
    Args:
        reader_id: The ID of the reader containing the card.
        options: Options for the READ BINARY command.
        
    Returns:
        Dictionary with status and binary data.
    """
    # Check if reader exists
    if reader_id not in ["reader1", "reader2"]:
        raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    
    # Check if card is present
    if reader_id != "reader1":  # In our mock, only reader1 has a card
        raise HTTPException(status_code=400, detail="No card present in the specified reader")
    
    # Validate parameters
    if options.offset < 0 or options.offset > 32767:
        raise HTTPException(status_code=400, detail="Offset must be between 0 and 32767")
    
    if options.length <= 0 or options.length > 256:
        raise HTTPException(status_code=400, detail="Length must be between 1 and 256")
    
    # Mock implementation - would be replaced with actual hardware calls
    # Create READ BINARY APDU: 00 B0 MSB(offset) LSB(offset) Length
    high_offset = (options.offset >> 8) & 0xFF
    low_offset = options.offset & 0xFF
    command = f"00 B0 {high_offset:02X} {low_offset:02X} {options.length:02X}"
    
    # Generate mock data
    import hashlib
    hash_input = f"{reader_id}{options.offset}{options.length}".encode()
    hash_obj = hashlib.md5(hash_input)
    mock_data = hash_obj.hexdigest()[:options.length * 2]
    
    # Format mock data with spaces
    formatted_data = " ".join([mock_data[i:i+2] for i in range(0, len(mock_data), 2)])
    response = f"{formatted_data} 90 00"
    
    return {
        "status": "success",
        "data": {
            "reader_id": reader_id,
            "command": command,
            "response": response,
            "sw": "9000",  # Status Word
            "binary_data": mock_data,
            "offset": options.offset,
            "length": options.length
        }
    }

@router.get("/smartcard/atr/{reader_id}", summary="Get ATR from smartcard")
@handle_errors
async def get_smartcard_atr(reader_id: str):
    """
    Get the Answer To Reset (ATR) from a smartcard.
    
    Args:
        reader_id: The ID of the reader containing the card.
        
    Returns:
        Dictionary with status and ATR information.
    """
    # Check if reader exists
    if reader_id not in ["reader1", "reader2"]:
        raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    
    # Check if card is present
    if reader_id != "reader1":  # In our mock, only reader1 has a card
        raise HTTPException(status_code=400, detail="No card present in the specified reader")
    
    # Mock implementation - would be replaced with actual hardware calls
    atr = "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 01 00 00 00 00 6A"
    
    # Parse ATR (in a real implementation this would be more detailed)
    atr_info = {
        "atr": atr,
        "historical_bytes": "A0 00 00 03 06 03 00 01 00 00 00 00",
        "t0_supported": True,
        "t1_supported": True,
        "card_type": "JavaCard"
    }
    
    return {
        "status": "success",
        "data": atr_info
    }