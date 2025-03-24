from fastapi import HTTPException
from functools import wraps
import traceback
import logging
from typing import Callable, Any

from backend.logging.logging_config import get_api_logger

# Get logger
logger = get_api_logger("utils")

def handle_errors(func: Callable) -> Callable:
    """
    Decorator that wraps API endpoints to handle exceptions uniformly.
    
    Args:
        func: The function to wrap.
        
    Returns:
        The wrapped function with error handling.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            # Call the original function
            return await func(*args, **kwargs)
        except HTTPException:
            # Let FastAPI handle HTTP exceptions normally
            raise
        except Exception as e:
            # Log the full error with traceback
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # Return a standardized error response
            return {
                "status": "error",
                "message": f"An error occurred: {str(e)}",
                "error_type": type(e).__name__
            }
    
    return wrapper

def validate_request_data(data: dict, required_fields: list) -> tuple:
    """
    Validates that all required fields are present in the request data.
    
    Args:
        data: The request data dictionary.
        required_fields: List of required field names.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    return True, ""

def format_success_response(data=None, message=None) -> dict:
    """
    Creates a standardized success response.
    
    Args:
        data: Optional data to include in the response.
        message: Optional message to include in the response.
        
    Returns:
        Standardized response dictionary.
    """
    response = {"status": "success"}
    
    if data is not None:
        response["data"] = data
    if message is not None:
        response["message"] = message
        
    return response

def format_error_response(message: str, error_code: str = None) -> dict:
    """
    Creates a standardized error response.
    
    Args:
        message: Error message to include in the response.
        error_code: Optional error code to include in the response.
        
    Returns:
        Standardized error response dictionary.
    """
    response = {
        "status": "error",
        "message": message
    }
    
    if error_code:
        response["error_code"] = error_code
        
    return response

def validate_json(data, schema):
    """
    Validate JSON data against a schema
    
    Args:
        data: The JSON data to validate
        schema: The schema to validate against
        
    Returns:
        Tuple of (is_valid, errors)
    """
    try:
        # Simple implementation that just checks for required fields
        if schema is None:
            return True, None
            
        required_fields = schema.get('required', [])
        missing_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
                
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
            
        return True, None
    except Exception as e:
        return False, str(e)