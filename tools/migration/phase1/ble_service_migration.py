import os
import shutil
import re
from pathlib import Path

# Define paths
SOURCE_FILE = r"k:\anita\poc\backend\modules\ble_manager.py"
TARGET_FILE = r"k:\anita\poc\backend\domain\services\ble_service.py"

def migrate_ble_service(dry_run=True):
    """Migrate the BLE Manager to a BLE Service."""
    # Read source file
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Transform content
    transformed = transform_manager_to_service(content)
    
    # Create target directory if it doesn't exist
    target_dir = os.path.dirname(TARGET_FILE)
    if not dry_run and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    if dry_run:
        print(f"Would write transformed content to: {TARGET_FILE}")
        print("First 500 characters of transformed content:")
        print(transformed[:500] + "...")
    else:
        # Write transformed content
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.write(transformed)
        print(f"Migrated BLE Manager to Service: {TARGET_FILE}")

def transform_manager_to_service(content):
    """Transform manager class content to service pattern."""
    # Create repository interface
    repo_interface = '''
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BleRepositoryInterface(ABC):
    """Interface for BLE device repositories."""
    
    @abstractmethod
    async def scan_devices(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Scan for available BLE devices."""
        pass
    
    @abstractmethod
    async def connect_device(self, device_id: str) -> bool:
        """Connect to a BLE device."""
        pass
    
    @abstractmethod
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a BLE device."""
        pass
'''
    
    # Add imports
    if "import" in content:
        # Find the last import
        last_import_idx = content.rfind("import")
        last_import_idx = content.find("\n", last_import_idx)
        
        # Add our imports after the last import
        additional_imports = "\nfrom typing import Optional, List, Dict, Any\n"
        content = content[:last_import_idx+1] + additional_imports + repo_interface + content[last_import_idx+1:]
    else:
        content = "from typing import Optional, List, Dict, Any\n" + repo_interface + content
    
    # Replace class name
    content = content.replace("BleManager", "BleService")
    
    # Replace classmethods with instance methods
    content = content.replace("@classmethod", "")
    content = content.replace("def ", "async def ", content.count("def "))
    content = content.replace("cls,", "self,")
    content = re.sub(r"cls\.", "self.", content)
    
    # Add constructor with DI
    constructor = '''
    def __init__(self, repository: Optional[BleRepositoryInterface] = None, logger = None):
        """Initialize the BLE service with dependencies."""
        self.repository = repository
        self.logger = logger
'''
    # Find the class definition and add constructor after it
    class_def_idx = content.find("class BleService")
    class_body_idx = content.find(":", class_def_idx)
    
    content = content[:class_body_idx+1] + constructor + content[class_body_idx+1:]
    
    # Modify methods to use repository
    content = content.replace("# Scan for BLE devices", 
                            "# Use repository if available\n        if self.repository:\n            return await self.repository.scan_devices(timeout)\n        \n        # Fallback to original implementation")
    
    return content

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    migrate_ble_service(dry_run)