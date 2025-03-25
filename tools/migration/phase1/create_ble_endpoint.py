import os
import shutil

# Define paths
SOURCE_FILE = r"k:\anita\poc\backend\routes\api\ble_routes.py"
TARGET_FILE = r"k:\anita\poc\backend\api\endpoints\ble.py"

def migrate_ble_endpoint(dry_run=True):
    """Migrate the BLE routes to a FastAPI endpoint."""
    # Read source file 
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Transform content
    transformed = transform_routes_to_endpoint(content)
    
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
        print(f"Migrated BLE routes to endpoint: {TARGET_FILE}")

def transform_routes_to_endpoint(content):
    """Transform routes to use dependency injection."""
    # Add imports for DI
    di_imports = """from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from backend.domain.services.ble_service import BleService
from backend.core.dependencies import get_ble_service
"""
    
    # Add imports at the top
    if "import" in content:
        import_end_idx = content.find("\n\n", content.find("import"))
        if import_end_idx == -1:
            import_end_idx = content.find("\n", content.find("import"))
        content = content[:import_end_idx+1] + di_imports + content[import_end_idx+1:]
    else:
        content = di_imports + content
    
    # Replace direct manager calls with service injection
    content = content.replace("BleManager.", "ble_service.")
    
    # Add dependency injection to route functions
    content = content.replace("async def scan", 
                            "async def scan", 1)
    content = content.replace("async def connect", 
                            "async def connect", 1)
    
    # Add the dependency parameter to each function
    content = content.replace("):", ", ble_service: BleService = Depends(get_ble_service)):", content.count("):"))
    
    return content

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    migrate_ble_endpoint(dry_run)