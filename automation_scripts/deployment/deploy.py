"""
Deployment script for Smart Card Manager
Helps set up and deploy the application in different environments
"""

import os
import sys
import argparse
import shutil
import json
import subprocess
from pathlib import Path
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
logger = logging.getLogger(__name__)

def create_env_file(env_type, host, port, log_level, admin_key):
    """
    Create environment file for deployment.

    Args:
        env_type (str): The environment type (development, testing, production).
        host (str): The host address.
        port (int): The port number.
        log_level (str): The logging level.
        admin_key (str, optional): The admin key. Defaults to None.

    Returns:
        str: The filename of the created environment file.

    Raises:
        ValueError: If the environment type is invalid.
        OSError: If there is an issue creating the environment file.
    """
    logger.info(f"Creating environment file for {env_type} environment.")
    if env_type not in ['development', 'testing', 'production']:
        logger.error(f"Invalid environment type: {env_type}")
        raise ValueError(f"Invalid environment type: {env_type}")
    
    env_vars = {
        'SMARTY_ENV': env_type,
        'SMARTY_HOST': host,
        'SMARTY_PORT': str(port),  # Ensure port is a string
        'SMARTY_LOG_LEVEL': log_level,
        'SMARTY_ADMIN_KEY': admin_key or 'change-me-in-production',
        'SMARTY_SECRET_KEY': os.urandom(24).hex(),
    }
    
    if env_type == 'production':
        # Add production-specific settings
        env_vars['SMARTY_PIN_KEY'] = os.urandom(16).hex()
    
    filename = '.env'
    try:
        with open(filename, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        logger.info(f"Created environment file: {filename}")
        return filename
    except OSError as e:
        logger.error(f"Failed to create environment file: {e}\n{traceback.format_exc()}")
        raise OSError(f"Failed to create environment file: {e}")

def create_systemd_service(name, user, path):
    """
    Create systemd service file for Linux deployment.

    Args:
        name (str): The name of the service.
        user (str): The user to run the service as.
        path (str): The path to the application directory.

    Returns:
        str: The filename of the created systemd service file.

    Raises:
        OSError: If there is an issue creating the systemd service file.
    """
    logger.info(f"Creating systemd service file: {name}.service for user {user} at path {path}")
    service_content = f"""[Unit]
Description=Smart Card Manager Service
After=network.target

[Service]
User={user}
WorkingDirectory={path}
ExecStart=/usr/bin/python3 {path}/app/smart.py
Restart=always
Environment=PYTHONUNBUFFERED=1
EnvironmentFile={path}/.env

[Install]
WantedBy=multi-user.target
"""
    
    filename = f"{name}.service"
    try:
        with open(filename, 'w') as f:
            f.write(service_content)
        logger.info(f"Created systemd service file: {filename}")
        logger.info(f"To install, copy to /etc/systemd/system/ and run: sudo systemctl enable {name}")
        return filename
    except OSError as e:
        logger.error(f"Failed to create systemd service file: {e}\n{traceback.format_exc()}")
        raise OSError(f"Failed to create systemd service file: {e}")

def create_windows_service(name, path):
    """Create Windows service configuration"""
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import socket
    
    nssm_cmd = f"nssm install {name} python {path}\\app\\smart.py"
    logger.info(f"To install as a Windows service, you can use NSSM with this command:")
    logger.info(nssm_cmd)
    logger.info(f"Or run this Python command: python -m pip install pywin32 && python {path}\\win_service.py install")
    
    # Create win_service.py file
    service_content = """import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import logging
from pathlib import Path

# Configure logging for the service
logging.basicConfig(level=logging.INFO,
                    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'win_service.log'),
                    format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

class SmartCardService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SmartCardManager"
    _svc_display_name_ = "Smart Card Manager Service"
    _svc_description_ = "Manages smart card lifecycle operations"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = False

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        logger.info("Service is stopping...")

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.is_running = True
        logger.info("Service is starting...")
        
        # Start the Smart Card Manager
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'smart.py')
            self.process = subprocess.Popen([sys.executable, script_path])
            logger.info(f"Started smart.py with PID {self.process.pid}")
            
            # Wait for stop signal
            while self.is_running:
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    # Stop signal received
                    break
            
            # Terminate the process
            if self.process:
                self.process.terminate()
                logger.info("Terminated smart.py process")
        except Exception as e:
            logger.error(f"Error running service: {e}")
            servicemanager.LogErrorMsg(f"Error running service: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SmartCardService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SmartCardService)
"""
    
    service_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services', 'win_service.py')
    try:
        with open(service_path, 'w') as f:
            f.write(service_content)
        logger.info("Created Windows service script: win_service.py")
        return 'win_service.py'
    except Exception as e:
        logger.error(f"Failed to create Windows service script: {e}")
        raise

def deploy():
    """Deploys the Smart Card Manager application, including copying necessary files and setting up configurations."""

    try:
        logger.info("Starting deployment tasks...")

        # Define source and destination paths
        source_dir = Path(__file__).resolve().parent
        app_dir = source_dir / "app"
        destination_dir = Path(os.getcwd())  # Deploy to current working directory

        # Defensive check: Ensure source directory exists
        if not app_dir.is_dir():
            raise FileNotFoundError(f"The application source directory '{app_dir}' was not found.")

        # Copy application files
        logger.info(f"Copying application files from '{app_dir}' to '{destination_dir}'...")
        try:
            shutil.copytree(app_dir, destination_dir / "app", dirs_exist_ok=True)
            logger.info("Application files copied successfully.")
        except Exception as e:
            raise Exception(f"Failed to copy application files: {e}")

        # Example: Run a command (replace with actual deployment commands)
        logger.info("Running post-copy configuration tasks...")
        try:
            subprocess.run(["echo", "Post-copy configuration complete!"], check=True)
            logger.info("Post-copy configuration tasks completed.")
        except subprocess.CalledProcessError as e:
            raise Exception(f"A post-copy configuration command failed: {e}")
        
        logger.info("Deployment completed successfully.")

    except FileNotFoundError as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed: A subprocess command failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment failed: An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        logger.info("Deployment process finished.")

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy Smart Card Manager")
    
    parser.add_argument(
        "--env", 
        choices=["development", "testing", "production"],
        default="development",
        help="Deployment environment"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Server port (default: 5000)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--admin-key",
        help="Admin key for secured operations"
    )
    
    parser.add_argument(
        "--service-name",
        default="smartcard-manager",
        help="Service name for system service installation"
    )
    
    parser.add_argument(
        "--service-user",
        default=os.environ.get("USER", "nobody"),
        help="User to run the service as (Linux only, default: current user)"
    )
    
    args = parser.parse_args()
    
    # Create environment file
    try:
        env_file = create_env_file(
            args.env,
            args.host,
            args.port,
            args.log_level,
            args.admin_key
        )
    except Exception as e:
        logger.error(f"Failed to create environment file: {e}")
        sys.exit(1)
    
    # Create service files based on platform
    try:
        if os.name == 'nt':  # Windows
            service_file = create_windows_service(
                args.service_name,
                os.path.abspath(os.path.dirname(__file__))
            )
        else:  # Linux/Mac
            service_file = create_systemd_service(
                args.service_name,
                args.service_user,
                os.path.abspath(os.path.dirname(__file__))
            )
    except Exception as e:
        logger.error(f"Failed to create service file: {e}")
        sys.exit(1)
    
    logger.info("\nDeployment files created successfully!")
    logger.info(f"Environment: {args.env}")
    logger.info(f"Host: {args.host}:{args.port}")
    
    if args.env == "production":
        logger.warning("\nPRODUCTION DEPLOYMENT CHECKLIST:")
        logger.warning("1. Set secure admin key and secret key in .env file")
        logger.warning("2. Configure proper logging")
        logger.warning("3. Set up a reverse proxy (Nginx/Apache) for HTTPS")
        logger.warning("4. Install as a system service for automatic startup")
    
    return 0

if __name__ == "__main__":
    deploy()
    sys.exit(main())