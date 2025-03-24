import logging
import os
import sys
from datetime import datetime

# Set up default logging directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Define log formats
CONSOLE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
FILE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Define log levels
LOG_LEVEL = logging.INFO
DEBUG_ENABLED = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')

if DEBUG_ENABLED:
    LOG_LEVEL = logging.DEBUG

def setup_logging() -> logging.Logger:
    """
    Configure and set up application-wide logging.
    
    Returns:
        The configured root logger.
    """
    # Create a timestamp for the log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"app_{timestamp}.log"
    log_file_path = os.path.join(LOG_DIR, log_filename)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Remove any existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(LOG_LEVEL)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    
    # Create file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
    
    # Add handlers to the root logger
    root_logger.addHandler(console)
    root_logger.addHandler(file_handler)
    
    # Log startup information
    root_logger.info(f"Logging initialized. Log file: {log_file_path}")
    if DEBUG_ENABLED:
        root_logger.info("Debug mode enabled")
    
    return root_logger

def get_api_logger(name: str = "api") -> logging.Logger:
    """
    Get a logger for API components.
    
    Args:
        name: Logger name, will be prefixed with 'api.' unless it contains a dot.
        
    Returns:
        The configured logger instance.
    """
    if name and '.' not in name:
        name = f"api.{name}"
    else:
        name = "api"
    
    logger = logging.getLogger(name)
    return logger

def log_request(request, logger=None):
    """
    Log details about an incoming request.
    
    Args:
        request: The FastAPI request object.
        logger: Optional logger to use.
    """
    if logger is None:
        logger = get_api_logger("request")
    
    logger.debug(f"Request: {request.method} {request.url}")
    logger.debug(f"Client: {request.client.host}:{request.client.port}")
    logger.debug(f"Headers: {request.headers}")

def log_response(response, logger=None):
    """
    Log details about an outgoing response.
    
    Args:
        response: The response object.
        logger: Optional logger to use.
    """
    if logger is None:
        logger = get_api_logger("response")
    
    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response headers: {response.headers}")