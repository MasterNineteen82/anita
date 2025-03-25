import os

# Define paths
TARGET_FILE = r"k:\anita\poc\backend\core\dependencies.py"

def create_dependencies(dry_run=True):
    """Create the dependencies module for DI."""
    content = '''from typing import Optional
from fastapi import Depends

# Import services
from backend.domain.services.ble_service import BleService

# Import repositories
from backend.infrastructure.repositories.ble_repository import BleRepository

# Create repository instances
_ble_repository = BleRepository()

# Service dependencies
def get_ble_service() -> BleService:
    """Get the BLE service instance with dependencies."""
    return BleService(repository=_ble_repository)
'''
    
    # Create target directory if it doesn't exist
    target_dir = os.path.dirname(TARGET_FILE)
    
    if dry_run:
        print(f"Would create directory: {target_dir}")
        print(f"Would write dependencies to: {TARGET_FILE}")
        print("Content to be written:")
        print(content)
    else:
        os.makedirs(target_dir, exist_ok=True)
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created dependencies module: {TARGET_FILE}")

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    create_dependencies(dry_run)