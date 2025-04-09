"""
Bluetooth Adapter Checker and Resource Manager.
Handles checking for and releasing Bluetooth adapters that might be in use by other applications.
"""
import asyncio
import logging
import os
import platform
import subprocess
import sys
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class BluetoothResourceManager:
    """Manages Bluetooth resources and ensures they're available for the application."""
    
    def __init__(self):
        self.system = platform.system()
        self.logger = logging.getLogger(__name__)
    
    async def check_and_release_adapters(self) -> bool:
        """
        Check for Bluetooth adapters in use and attempt to release them.
        
        Returns:
            bool: True if adapters are available or were successfully released
        """
        if self.system == "Windows":
            return await self._check_and_release_windows()
        elif self.system == "Linux":
            return await self._check_and_release_linux()
        elif self.system == "Darwin":  # macOS
            return await self._check_and_release_macos()
        else:
            self.logger.warning(f"Unsupported platform: {self.system}")
            return False
    
    async def _check_and_release_windows(self) -> bool:
        """
        Check for Bluetooth processes on Windows and attempt to release them.
        
        Returns:
            bool: True if successful
        """
        self.logger.info("Checking for Bluetooth processes on Windows")
        
        # Get list of Bluetooth-related processes
        bt_processes = await self._get_windows_bt_processes()
        
        if not bt_processes:
            self.logger.info("No conflicting Bluetooth processes found")
            return True
        
        self.logger.warning(f"Found {len(bt_processes)} Bluetooth processes that might conflict")
        for proc in bt_processes:
            self.logger.info(f"- {proc['name']} (PID: {proc['pid']})")
        
        # Ask user if they want to try to release these resources
        print("\nThe following Bluetooth-related processes might be using the adapter:")
        for proc in bt_processes:
            print(f"- {proc['name']} (PID: {proc['pid']})")
        
        # Return status - we don't automatically kill processes as that could be disruptive
        return len(bt_processes) == 0
    
    async def _get_windows_bt_processes(self) -> List[Dict[str, any]]:
        """Get list of processes that might be using Bluetooth on Windows."""
        processes = []
        
        # Common Bluetooth-related process names
        bt_process_names = [
            "Bluetooth",
            "bluetoothd",
            "BtwRSupportService",
            "BtwGatherDebug",
            "BluetoothAudioGateway",
            "fsquirt",  # Windows Bluetooth file transfer
            "RuntimeBroker",  # Can handle Bluetooth
            "btvstack",
            "BtvStack",
            "BTTray",
            "BTStackServer"
        ]
        
        try:
            # Use PowerShell to get process info
            cmd = "powershell -Command \"Get-Process | Select-Object Name, Id | ConvertTo-Json\""
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                self.logger.error(f"Error getting process list: {stderr.decode()}")
                return processes
            
            import json
            all_processes = json.loads(stdout.decode())
            
            # Filter to only Bluetooth-related processes
            for process in all_processes:
                for bt_name in bt_process_names:
                    if bt_name.lower() in process['Name'].lower():
                        processes.append({
                            'name': process['Name'],
                            'pid': process['Id']
                        })
                        break
            
            return processes
        except Exception as e:
            self.logger.error(f"Error checking Bluetooth processes: {e}")
            return []

    async def _check_and_release_linux(self) -> bool:
        """
        Check for Bluetooth processes on Linux and attempt to release them.
        
        Returns:
            bool: True if successful
        """
        self.logger.info("Checking for Bluetooth processes on Linux")
        # Implementation for Linux would be here
        return True
    
    async def _check_and_release_macos(self) -> bool:
        """
        Check for Bluetooth processes on macOS and attempt to release them.
        
        Returns:
            bool: True if successful
        """
        self.logger.info("Checking for Bluetooth processes on macOS")
        # Implementation for macOS would be here
        return True

async def check_bluetooth_resources():
    """Check Bluetooth resources and inform user of potential conflicts."""
    manager = BluetoothResourceManager()
    await manager.check_and_release_adapters()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(check_bluetooth_resources())
