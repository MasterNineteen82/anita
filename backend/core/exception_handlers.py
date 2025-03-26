from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import traceback

logger = logging.getLogger("exception_handler")

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent application crashes."""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    
    # Return a generic error response
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An internal server error occurred", 
                "detail": str(exc) if not isinstance(exc, AssertionError) else "Internal assertion failed"}
    )