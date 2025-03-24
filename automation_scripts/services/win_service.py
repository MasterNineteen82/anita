import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import logging
from pathlib import Path

class SmartCardService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SmartCardManager"
    _svc_display_name_ = "Smart Card Manager Service"
    _svc_description_ = "Manages smart card lifecycle operations"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = False
        
        # Set up logging
        log_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'logs'
        os.makedirs(log_dir, exist_ok=True)
        log_file = str(log_dir / 'win_service.log')
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('smartcard_service')

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        self.logger.info("Service is stopping...")

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.is_running = True
        self.logger.info("Service is starting...")
        
        # Start the Smart Card Manager
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart.py')
            self.process = subprocess.Popen([sys.executable, script_path])
            self.logger.info(f"Started smart.py with PID {self.process.pid}")
            
            # Wait for stop signal
            while self.is_running:
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    # Stop signal received
                    break
            
            # Terminate the process
            if self.process:
                self.process.terminate()
                self.logger.info("Terminated smart.py process")
        except Exception as e:
            self.logger.error(f"Error running service: {e}")
            servicemanager.LogErrorMsg(f"Error running service: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SmartCardService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SmartCardService)