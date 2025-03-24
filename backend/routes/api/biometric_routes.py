from fastapi import APIRouter, HTTPException, Request, Body, File, UploadFile, Form
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
import base64
import time
import random
from datetime import datetime

from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors

# Define router with proper prefix and tags
router = APIRouter(tags=["biometric"])

# Get logger
logger = get_api_logger("biometric")

# Models for biometric operations
class BiometricTemplate(BaseModel):
    template_id: str
    biometric_type: str
    template_format: str
    template_data: str  # Base64 encoded data
    quality_score: float
    created_at: datetime

class BiometricEnrollRequest(BaseModel):
    user_id: str
    biometric_type: str
    template_data: Optional[str] = None  # Base64 encoded data
    metadata: Optional[Dict[str, Any]] = None

class BiometricVerifyRequest(BaseModel):
    user_id: str
    biometric_type: str
    sample_data: str  # Base64 encoded data

class BiometricIdentifyRequest(BaseModel):
    biometric_type: str
    sample_data: str  # Base64 encoded data
    threshold: Optional[float] = 0.7

# Routes for biometric operations
@router.get("/biometric/supported", summary="Get supported biometric types")
@handle_errors
async def get_supported_biometrics():
    """
    Get a list of supported biometric types.
    
    Returns:
        Dictionary with status and supported biometric types.
    """
    supported_types = [
        {
            "type": "fingerprint",
            "display_name": "Fingerprint",
            "available": True,
            "supported_formats": ["ISO-19794-2", "ANSI-378"]
        },
        {
            "type": "face",
            "display_name": "Face Recognition",
            "available": True,
            "supported_formats": ["ISO-19794-5"]
        },
        {
            "type": "iris",
            "display_name": "Iris Recognition",
            "available": False,
            "supported_formats": ["ISO-19794-6"]
        },
        {
            "type": "voice",
            "display_name": "Voice Recognition",
            "available": True,
            "supported_formats": ["custom"]
        }
    ]
    
    return {
        "status": "success",
        "data": supported_types
    }

@router.get("/biometric/devices", summary="Get connected biometric devices")
@handle_errors
async def get_biometric_devices():
    """
    Get a list of connected biometric devices.
    
    Returns:
        Dictionary with status and connected devices.
    """
    devices = [
        {
            "device_id": "fp-scanner-1",
            "device_type": "fingerprint",
            "name": "DigitalPersona U.are.U 4500",
            "status": "ready",
            "connection_type": "USB",
            "firmware_version": "2.1.4"
        },
        {
            "device_id": "camera-1",
            "device_type": "face",
            "name": "Logitech HD Pro Webcam C920",
            "status": "ready",
            "connection_type": "USB",
            "firmware_version": "8.0.1"
        }
    ]
    
    return {
        "status": "success",
        "data": devices
    }

@router.get("/biometric/device/{device_id}", summary="Get biometric device info")
@handle_errors
async def get_biometric_device_info(device_id: str):
    """
    Get information about a specific biometric device.
    
    Args:
        device_id: The ID of the biometric device.
        
    Returns:
        Dictionary with status and device information.
    """
    # Check if device exists
    if device_id not in ["fp-scanner-1", "camera-1"]:
        raise HTTPException(status_code=404, detail=f"Biometric device with ID {device_id} not found")
    
    if device_id == "fp-scanner-1":
        device_info = {
            "device_id": "fp-scanner-1",
            "device_type": "fingerprint",
            "name": "DigitalPersona U.are.U 4500",
            "status": "ready",
            "connection_type": "USB",
            "firmware_version": "2.1.4",
            "resolution": "512 dpi",
            "image_dimensions": "355 x 390",
            "supported_formats": ["ISO-19794-2", "ANSI-378"]
        }
    else:  # camera-1
        device_info = {
            "device_id": "camera-1",
            "device_type": "face",
            "name": "Logitech HD Pro Webcam C920",
            "status": "ready",
            "connection_type": "USB",
            "firmware_version": "8.0.1",
            "resolution": "1080p",
            "frame_rate": 30,
            "supported_formats": ["ISO-19794-5"]
        }
    
    return {
        "status": "success",
        "data": device_info
    }

@router.post("/biometric/capture/{biometric_type}", summary="Capture biometric sample")
@handle_errors
async def capture_biometric(
    biometric_type: str,
    device_id: Optional[str] = None,
    quality_threshold: Optional[float] = 0.6
):
    """
    Capture a biometric sample from a connected device.
    
    Args:
        biometric_type: Type of biometric to capture (fingerprint, face, etc.).
        device_id: Optional device ID to use for capture.
        quality_threshold: Minimum quality threshold for the capture.
        
    Returns:
        Dictionary with status and captured sample information.
    """
    # Validate biometric type
    valid_types = ["fingerprint", "face", "iris", "voice"]
    if biometric_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid biometric type. Must be one of: {', '.join(valid_types)}"
        )
    
    # If device specified, check if it exists and matches biometric type
    if device_id:
        if device_id not in ["fp-scanner-1", "camera-1"]:
            raise HTTPException(status_code=404, detail=f"Biometric device with ID {device_id} not found")
        
        if (biometric_type == "fingerprint" and device_id != "fp-scanner-1") or \
           (biometric_type == "face" and device_id != "camera-1"):
            raise HTTPException(
                status_code=400,
                detail=f"Device {device_id} does not support {biometric_type} biometrics"
            )
    else:
        # Auto-select a device based on biometric type
        if biometric_type == "fingerprint":
            device_id = "fp-scanner-1"
        elif biometric_type == "face":
            device_id = "camera-1"
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No device available for {biometric_type} biometrics"
            )
    
    # Mock implementation - would be replaced with actual hardware calls
    # Simulate a capture delay
    import asyncio
    await asyncio.sleep(1.5)
    
    # Generate mock data
    quality_score = random.uniform(0.6, 0.95)
    
    # Mock capture failed if quality below threshold
    if quality_score < quality_threshold:
        return {
            "status": "error",
            "message": f"Captured sample quality ({quality_score:.2f}) below threshold ({quality_threshold})",
            "data": {
                "device_id": device_id,
                "biometric_type": biometric_type,
                "quality_score": quality_score,
                "quality_passed": False
            }
        }
    
    # Generate some random data as the biometric template
    mock_template = base64.b64encode(os.urandom(1024)).decode('utf-8')
    
    # Mock image data (would be a real image in production)
    mock_image = None
    if biometric_type in ["fingerprint", "face"]:
        # In a real application, this would be a base64-encoded image
        mock_image = base64.b64encode(os.urandom(5120)).decode('utf-8')
    
    capture_result = {
        "device_id": device_id,
        "biometric_type": biometric_type,
        "quality_score": quality_score,
        "quality_passed": True,
        "capture_time": datetime.now().isoformat(),
        "template": mock_template,
        "image": mock_image
    }
    
    return {
        "status": "success",
        "message": f"{biometric_type.capitalize()} sample captured successfully",
        "data": capture_result
    }

@router.post("/biometric/enroll", summary="Enroll biometric template")
@handle_errors
async def enroll_biometric(request: BiometricEnrollRequest):
    """
    Enroll a biometric template for a user.
    
    Args:
        request: Enrollment request containing user ID and biometric data.
        
    Returns:
        Dictionary with status and enrollment information.
    """
    # Validate biometric type
    valid_types = ["fingerprint", "face", "iris", "voice"]
    if request.biometric_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid biometric type. Must be one of: {', '.join(valid_types)}"
        )
    
    # In a real implementation, you would process the template data
    # For this mock, we'll generate a template ID and store the data
    template_id = f"{request.biometric_type}-{request.user_id}-{int(time.time())}"
    
    # If template_data is not provided, generate a random one (in real app, would capture)
    template_data = request.template_data
    if not template_data:
        template_data = base64.b64encode(os.urandom(1024)).decode('utf-8')
    
    # Mock implementation - would be replaced with actual database storage
    enroll_result = {
        "user_id": request.user_id,
        "template_id": template_id,
        "biometric_type": request.biometric_type,
        "enrolled_at": datetime.now().isoformat(),
        "quality_score": round(random.uniform(0.7, 0.98), 2)
    }
    
    return {
        "status": "success",
        "message": f"{request.biometric_type.capitalize()} enrolled successfully for user {request.user_id}",
        "data": enroll_result
    }

@router.post("/biometric/verify", summary="Verify biometric identity")
@handle_errors
async def verify_biometric(request: BiometricVerifyRequest):
    """
    Verify a user's identity using biometric data.
    
    Args:
        request: Verification request containing user ID and biometric sample.
        
    Returns:
        Dictionary with status and verification result.
    """
    # Validate biometric type
    valid_types = ["fingerprint", "face", "iris", "voice"]
    if request.biometric_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid biometric type. Must be one of: {', '.join(valid_types)}"
        )
    
    # In a real implementation, you would compare the sample with stored templates
    # For this mock, we'll generate a random match score and verify based on the user_id
    
    # First, check if user exists (for demo, accept any user ID ending in odd number)
    user_id_last_char = request.user_id[-1]
    user_exists = user_id_last_char.isdigit() and int(user_id_last_char) % 2 == 1
    
    if not user_exists:
        return {
            "status": "error",
            "message": f"User {request.user_id} not found or has no {request.biometric_type} templates enrolled",
            "data": {
                "verified": False,
                "reason": "user_not_found"
            }
        }
    
    # Generate match score - slightly randomized but high for demo purposes
    match_score = round(random.uniform(0.75, 0.98), 3)
    threshold = 0.7  # Configurable verification threshold
    
    verify_result = {
        "user_id": request.user_id,
        "biometric_type": request.biometric_type,
        "verified": match_score >= threshold,
        "match_score": match_score,
        "threshold": threshold,
        "verification_time": datetime.now().isoformat()
    }
    
    if match_score >= threshold:
        message = f"User {request.user_id} successfully verified with {request.biometric_type}"
    else:
        message = f"Verification failed for user {request.user_id}"
    
    return {
        "status": "success",
        "message": message,
        "data": verify_result
    }

@router.post("/biometric/identify", summary="Identify using biometric data")
@handle_errors
async def identify_biometric(request: BiometricIdentifyRequest):
    """
    Identify a user using only biometric data (1:N match).
    
    Args:
        request: Identification request containing biometric sample.
        
    Returns:
        Dictionary with status and identification results.
    """
    # Validate biometric type
    valid_types = ["fingerprint", "face", "iris", "voice"]
    if request.biometric_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid biometric type. Must be one of: {', '.join(valid_types)}"
        )
    
    # In a real implementation, you would compare the sample with all stored templates
    # For this mock, we'll identify one or more potential matches with confidence scores
    
    # Simulate identification delay
    import asyncio
    await asyncio.sleep(2)
    
    # Set identification threshold (minimum score to include in results)
    threshold = request.threshold if request.threshold is not None else 0.7
    
    # Generate mock identification results
    # For demo, include 0-3 candidates based on random chance
    num_candidates = random.choices([0, 1, 2, 3], weights=[0.2, 0.5, 0.2, 0.1])[0]
    
    candidates = []
    for i in range(num_candidates):
        # Generate a user ID and score - scores decrease with candidate index
        user_id = f"user{random.randint(1000, 9999)}"
        score = round(random.uniform(max(0.5, threshold), 0.99) * (1.0 - (i * 0.1)), 3)
        candidates.append({
            "user_id": user_id,
            "match_score": score,
            "biometric_type": request.biometric_type
        })
    
    # Sort candidates by descending score
    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Determine if identification was successful (at least one candidate above threshold)
    identified = len(candidates) > 0 and candidates[0]["match_score"] >= threshold
    
    identify_result = {
        "identified": identified,
        "candidates": candidates,
        "threshold": threshold,
        "identification_time": datetime.now().isoformat()
    }
    
    if identified:
        message = f"User identified with {request.biometric_type}: {candidates[0]['user_id']}"
    else:
        message = "No matching user found"
    
    return {
        "status": "success",
        "message": message,
        "data": identify_result
    }

@router.get("/biometric/templates/{user_id}", summary="Get user's biometric templates")
@handle_errors
async def get_user_templates(user_id: str, biometric_type: Optional[str] = None):
    """
    Get all biometric templates for a user.
    
    Args:
        user_id: The ID of the user.
        biometric_type: Optional filter for specific biometric type.
        
    Returns:
        Dictionary with status and template information.
    """
    # In a real implementation, you would fetch the templates from a database
    # For this mock, we'll generate some random templates
    
    # First, check if user exists (for demo, accept any user ID ending in odd number)
    user_id_last_char = user_id[-1]
    user_exists = user_id_last_char.isdigit() and int(user_id_last_char) % 2 == 1
    
    if not user_exists:
        return {
            "status": "error",
            "message": f"User {user_id} not found",
            "data": {
                "templates": []
            }
        }
    
    # Generate mock templates
    templates = []
    
    # Fingerprint templates
    if not biometric_type or biometric_type == "fingerprint":
        for i in range(2):  # Two fingerprints enrolled
            finger_position = "right_index" if i == 0 else "right_thumb"
            templates.append({
                "template_id": f"fp-{user_id}-{finger_position}",
                "biometric_type": "fingerprint",
                "finger_position": finger_position,
                "quality_score": round(random.uniform(0.7, 0.95), 2),
                "enrolled_at": (datetime.now().replace(day=1) if i == 0 else datetime.now()).isoformat(),
                "format": "ISO-19794-2"
            })
    
    # Face template
    if not biometric_type or biometric_type == "face":
        templates.append({
            "template_id": f"face-{user_id}",
            "biometric_type": "face",
            "quality_score": round(random.uniform(0.7, 0.95), 2),
            "enrolled_at": datetime.now().isoformat(),
            "format": "ISO-19794-5"
        })
    
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "templates": templates
        }
    }

@router.delete("/biometric/template/{template_id}", summary="Delete biometric template")
@handle_errors
async def delete_template(template_id: str):
    """
    Delete a specific biometric template.
    
    Args:
        template_id: The ID of the template to delete.
        
    Returns:
        Dictionary with status and deletion confirmation.
    """
    # In a real implementation, you would delete the template from a database
    # For this mock, we'll check if the template ID follows our format
    
    valid_template = False
    biometric_type = None
    
    if template_id.startswith("fp-"):
        valid_template = True
        biometric_type = "fingerprint"
    elif template_id.startswith("face-"):
        valid_template = True
        biometric_type = "face"
    elif template_id.startswith("iris-"):
        valid_template = True
        biometric_type = "iris"
    elif template_id.startswith("voice-"):
        valid_template = True
        biometric_type = "voice"
    
    if not valid_template:
        raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
    
    return {
        "status": "success",
        "message": f"{biometric_type.capitalize()} template {template_id} deleted successfully",
        "data": {
            "template_id": template_id,
            "biometric_type": biometric_type
        }
    }

@router.post("/biometric/compare", summary="Compare two biometric samples")
@handle_errors
async def compare_biometric_samples(
    biometric_type: str,
    sample1: str,  # Base64 encoded sample
    sample2: str   # Base64 encoded sample
):
    """
    Compare two biometric samples and return a match score.
    
    Args:
        biometric_type: Type of biometric to compare.
        sample1: First biometric sample (base64 encoded).
        sample2: Second biometric sample (base64 encoded).
        
    Returns:
        Dictionary with status and comparison result.
    """
    # Validate biometric type
    valid_types = ["fingerprint", "face", "iris", "voice"]
    if biometric_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid biometric type. Must be one of: {', '.join(valid_types)}"
        )
    
    # In a real implementation, you would compare the actual biometric samples
    # For this mock, we'll generate a random match score
    match_score = round(random.uniform(0.3, 0.95), 3)
    
    comparison_result = {
        "biometric_type": biometric_type,
        "match_score": match_score,
        "comparison_time": datetime.now().isoformat()
    }
    
    return {
        "status": "success",
        "data": comparison_result
    }

# Add import for os module (needed for the random template generation)
import os