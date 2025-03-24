from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
from backend.security.security_manager import SecurityManager
from backend.security.fraud_detection import FraudDetection
from backend.models import StatusResponse, ErrorResponse, LogRequest, Settings
from ..utils import handle_errors, validate_json


logger = logging.getLogger(__name__)
router = APIRouter(tags=["security"])

class SecurityScanRequest(BaseModel):
    target: str
    scan_type: str
    options: Optional[Dict[str, Any]] = None

class FraudCheckRequest(BaseModel):
    transaction_id: str
    user_id: str
    transaction_data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

class EncryptRequest(BaseModel):
    data: str

class DecryptRequest(BaseModel):
    data: str

@router.post("/security/scan", summary="Run security scan")
@handle_errors
async def run_security_scan(request: SecurityScanRequest):
    """Run a security scan on a target"""
    security_manager = SecurityManager()
    scan_result = security_manager.run_scan(
        target=request.target,
        scan_type=request.scan_type,
        options=request.options
    )
    
    return {
        "status": "success",
        "data": scan_result
    }

@router.get("/security/status", summary="Get security subsystem status")
@handle_errors
async def get_security_status():
    """Get status of security subsystems"""
    security_manager = SecurityManager()
    status = security_manager.get_status()
    
    return {
        "status": "success",
        "data": status
    }

@router.post("/security/fraud/check", summary="Run fraud detection check")
@handle_errors
async def check_for_fraud(request: FraudCheckRequest):
    """Check a transaction for potential fraud"""
    fraud_detection = FraudDetection()
    result = fraud_detection.analyze_transaction(
        transaction_id=request.transaction_id,
        user_id=request.user_id,
        transaction_data=request.transaction_data,
        context=request.context
    )
    
    return {
        "status": "success",
        "data": {
            "fraud_score": result.get("score", 0.0),
            "risk_level": result.get("risk_level", "low"),
            "triggers": result.get("triggers", [])
        }
    }

@router.post("/security/encrypt", summary="Encrypt data")
@handle_errors
async def encrypt_data(request: EncryptRequest):
    """
    Encrypt the provided data.
    
    Args:
        request: The request containing data to encrypt
        
    Returns:
        Dictionary containing the encrypted data
    """
    result = await SecurityManager.encrypt_data(request.data)
    return result

@router.post("/security/decrypt", summary="Decrypt data")
@handle_errors
async def decrypt_data(request: DecryptRequest):
    """
    Decrypt the provided data.
    
    Args:
        request: The request containing data to decrypt
        
    Returns:
        Dictionary containing the decrypted data
    """
    result = await SecurityManager.decrypt_data(request.data)
    return result

@router.post("/security/verify", summary="Verify request security")
@handle_errors
async def verify_request(request: Request):
    """
    Verify the security of the incoming request.
    
    Returns:
        Dictionary containing verification results
    """
    request_data = await request.json()
    result = await SecurityManager.verify_request(request_data)
    return result