import logging
import os
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

# Set up default logging directory
LOG_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "logs"
ERROR_LOG_FILE = LOG_DIR / "errors.log"
ISSUE_LOG_FILE = LOG_DIR / "issues.json"
LOG_DIR.mkdir(exist_ok=True)

# Define log levels
LOG_LEVEL = logging.INFO
DEBUG_ENABLED = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')

if DEBUG_ENABLED:
    LOG_LEVEL = logging.DEBUG

# Define both emoji icons and ASCII alternatives
LOG_LEVEL_ICONS = {
    'DEBUG': '🔍',
    'INFO': 'ℹ️',
    'WARNING': '⚠️',
    'ERROR': '❌',
    'CRITICAL': '🔥'
}

ASCII_ICONS = {
    'DEBUG': '[D]',
    'INFO': '[I]',
    'WARNING': '[W]',
    'ERROR': '[E]',
    'CRITICAL': '[C]'
}

# Try to detect if terminal supports emoji
def supports_emoji():
    """Check if the terminal likely supports emoji"""
    # Allow emoji to be enabled via environment variable
    emoji_enabled = os.environ.get('ENABLE_EMOJI', '').lower() in ('true', '1', 't')
    if emoji_enabled:
        return True
        
    # Check for known emoji-supporting terminals
    term = os.environ.get('TERM', '')
    if 'xterm' in term or 'screen' in term:
        return True
    
    # Check for Windows Terminal
    if 'WT_SESSION' in os.environ:
        return True
    
    # Check if we're in VS Code
    if 'VSCODE_PID' in os.environ:
        return True
    
    # Check terminal name in Windows
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Get console mode
            mode = ctypes.c_uint()
            if kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), ctypes.byref(mode)):
                # Check if virtual terminal processing is enabled (supports ANSI)
                if mode.value & 0x0004:  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    return True
        except (AttributeError, OSError, ImportError):
            pass
    
    # Default to False on Windows, True elsewhere
    return os.name != 'nt'

# Use ASCII icons if emoji likely not supported
ICONS = LOG_LEVEL_ICONS if supports_emoji() else ASCII_ICONS

# Define colors for log levels (using ANSI color codes for broader compatibility)
LEVEL_COLORS = {
    'DEBUG': '\033[94m',    # Blue
    'INFO': '\033[92m',     # Green
    'WARNING': '\033[93m',  # Yellow
    'ERROR': '\033[91m',    # Red
    'CRITICAL': '\033[97;101m'  # White on Red
}

RESET_COLOR = '\033[0m'

# Define custom formatter with icons and colors - updated for tabular format
class EnhancedFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        # Column widths for better alignment
        self.timestamp_width = 23  # Width for timestamp column
        self.logger_width = 15     # Width for logger name column
        self.level_width = 8       # Width for log level column
    
    def format(self, record):
        # Get the appropriate icon and color
        icon = ICONS.get(record.levelname, '')
        color = LEVEL_COLORS.get(record.levelname, '')
        
        # Format timestamp
        timestamp = self.formatTime(record, self.datefmt)
        
        # Truncate or pad logger name for consistent width
        logger_name = record.name[:self.logger_width].ljust(self.logger_width)
        if not logger_name or logger_name == 'root':
            logger_name = 'main'.ljust(self.logger_width)
            
        # Format level name with consistent width
        level_name = record.levelname.ljust(self.level_width)
        
        # Get the message
        message = record.getMessage()
        
        # Create tabular format with columns
        if sys.stdout.isatty():  # Use colors in terminal
            formatted_line = (
                f"{color}{icon}{RESET_COLOR}  "
                f"{timestamp} │ "
                f"{logger_name} │ "
                f"{color}{level_name}{RESET_COLOR} │ "
                f"{message}"
            )
        else:
            formatted_line = (
                f"{icon}  "
                f"{timestamp} │ "
                f"{logger_name} │ "
                f"{level_name} │ "
                f"{message}"
            )
            
        # Handle exception info if present
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            
            # Add the formatted exception to our output, with proper indentation
            exc_lines = record.exc_text.split('\n')
            indent = ' ' * (self.timestamp_width + self.logger_width + self.level_width + 10)
            
            for i, line in enumerate(exc_lines):
                if i == 0:
                    formatted_line += f"\n{indent}{line}"
                else:
                    formatted_line += f"\n{indent}{line}"
                    
        return formatted_line

# Error tracker class
class ErrorTracker:
    def __init__(self, filename=ISSUE_LOG_FILE):
        self.filename = filename
        self.issues = self._load_issues()
        
    def _load_issues(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
        
    def add_issue(self, error_type, message, details=None):
        issue = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': message,
            'details': details or {}
        }
        
        # Check if this exact issue already exists
        for existing in self.issues:
            if (existing['type'] == issue['type'] and 
                existing['message'] == issue['message']):
                # Update timestamp of existing issue
                existing['timestamp'] = issue['timestamp']
                existing['count'] = existing.get('count', 1) + 1
                self._save_issues()
                return
                
        # If not found, add as new issue
        issue['count'] = 1
        self.issues.append(issue)
        self._save_issues()
        
    def _save_issues(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.issues, f, indent=2)
        except IOError as e:
            print(f"Failed to save issue log: {e}")

# Create global error tracker
error_tracker = ErrorTracker()

# Custom error handler
class ErrorLogHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            error_details = {
                'logger': record.name,
                'path': record.pathname,
                'line': record.lineno,
                'function': record.funcName
            }
            
            if record.exc_info:
                error_details['traceback'] = traceback.format_exception(*record.exc_info)
            
            error_tracker.add_issue(
                record.levelname,
                record.getMessage(),
                error_details
            )

def setup_logging() -> logging.Logger:
    """Set up logging configuration with colorful output and error tracking"""
    log_file = LOG_DIR / f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Create handlers
    file_handler = logging.FileHandler(log_file)
    error_file_handler = logging.FileHandler(ERROR_LOG_FILE, mode='a')
    error_file_handler.setLevel(logging.ERROR)
    
    # Create console handler with enhanced formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = EnhancedFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Create file handler with standard formatter
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    error_file_handler.setFormatter(file_formatter)
    
    # Set up logging configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)
    root_logger.addHandler(ErrorLogHandler())
    
    # Print a header for the log table
    timestamp_width = 23
    logger_width = 15
    level_width = 8
    
    if sys.stdout.isatty():
        header = (
            f"\n{'='*80}\n"
            f"TIMESTAMP{' '*(timestamp_width-9)} │ "
            f"{'LOGGER'.ljust(logger_width)} │ "
            f"{'LEVEL'.ljust(level_width)} │ "
            f"MESSAGE\n"
            f"{'-'*timestamp_width}-┼-"
            f"{'-'*logger_width}-┼-"
            f"{'-'*level_width}-┼-"
            f"{'-'*40}\n"
        )
        print(header)
    
    # Log startup message
    root_logger.info(f"Logging initialized. Log file: {log_file}")
    if DEBUG_ENABLED:
        root_logger.info("Debug mode enabled")
    
    return root_logger

def get_api_logger(name: str = "api") -> logging.Logger:
    """Get a logger for API routes"""
    return logging.getLogger(name)

def log_request(request, logger=None):
    """Log an incoming request"""
    if logger is None:
        logger = logging.getLogger()
    logger.info(f"Request: {request.method} {request.url}")

def log_response(response, logger=None):
    """Log an outgoing response"""
    if logger is None:
        logger = logging.getLogger()
    logger.info(f"Response: {response.status_code} {response.url}")

def log_error(message, exc_info=None, logger=None):
    """Log an error and track it in the issue log"""
    if logger is None:
        logger = logging.getLogger()
    logger.error(message, exc_info=exc_info)
    
def print_colorful_traceback(exc_info):
    """Print a colorful traceback to the console with better formatting"""
    if not exc_info:
        return
    
    import traceback
    
    # Use ANSI color codes directly for better compatibility
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    
    tb_lines = traceback.format_exception(*exc_info)
    print(f"\n{RED}{'='*80}{RESET}")
    print(f"{RED}EXCEPTION: {exc_info[1]}{RESET}")
    print(f"{RED}{'='*80}{RESET}")
    
    for line in tb_lines:
        # Highlight important parts
        line = line.replace("File", f"{CYAN}File{RESET}")
        line = line.replace("line", f"{CYAN}line{RESET}")
        line = line.replace("in", f"{CYAN}in{RESET}")
        
        # Print the formatted line
        print(line, end="")
    
    print(f"{RED}{'='*80}{RESET}\n")
