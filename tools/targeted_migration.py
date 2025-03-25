import json
import os
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"targeted_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_targeted_plan(python_files_json, output_file):
    """Create a targeted migration plan focusing on critical components first."""
    # Load the python files inventory
    with open(python_files_json, 'r') as f:
        python_files = json.load(f)
    
    # Create phased migration plan
    targeted_plan = {
        "phase1": {  # Critical functionality
            "title": "Critical Functionality (BLE and UI)",
            "services": [],
            "endpoints": [],
            "websockets": [],
            "utilities": []
        },
        "phase2": {  # Core functionality
            "title": "Core Business Logic",
            "services": [],
            "endpoints": [],
            "models": []
        },
        "phase3": {  # Supporting components
            "title": "Supporting Components",
            "utilities": [],
            "security": [],
            "config": []
        }
    }
    
    # Process all Python files
    for dir_path, files in python_files.get("directories", {}).items():
        for file_info in files:
            file_path = file_info.get("path", "")
            filename = os.path.basename(file_path)
            
            # Skip __init__.py and archived files
            if filename == "__init__.py" or ".archive" in file_path:
                continue
            
            # Determine component type and phase
            component_info = categorize_component(file_path, filename)
            if component_info:
                phase = component_info["phase"]
                category = component_info["category"]
                
                # Add to the appropriate phase and category
                if phase in targeted_plan and category in targeted_plan[phase]:
                    targeted_plan[phase][category].append({
                        "source": file_path,
                        "destination": component_info["destination"],
                        "transformation": component_info["transformation"],
                        "notes": component_info["notes"],
                        "priority": component_info.get("priority", "normal")
                    })
    
    # Generate stats for each phase
    for phase, data in targeted_plan.items():
        total_components = sum(len(data[cat]) for cat in data if cat != "title")
        data["stats"] = {
            "total_components": total_components,
            "categories": {cat: len(data[cat]) for cat in data if cat != "title" and cat != "stats"}
        }
    
    # Save the targeted plan
    with open(output_file, 'w') as f:
        json.dump(targeted_plan, f, indent=2)
    
    logger.info(f"Created targeted migration plan: {output_file}")
    logger.info(f"Phase 1: {targeted_plan['phase1']['stats']['total_components']} components")
    logger.info(f"Phase 2: {targeted_plan['phase2']['stats']['total_components']} components")
    logger.info(f"Phase 3: {targeted_plan['phase3']['stats']['total_components']} components")
    
    return targeted_plan

def categorize_component(file_path, filename):
    """Categorize a file into a component type and migration phase."""
    file_path_lower = file_path.lower()
    filename_lower = filename.lower()
    
    # Phase 1: Critical functionality (BLE and UI)
    
    # BLE Manager/Service
    if "_manager" in filename_lower and ("ble" in filename_lower or "bluetooth" in filename_lower):
        service_name = filename_lower.replace("_manager.py", "_service.py")
        return {
            "phase": "phase1",
            "category": "services",
            "destination": f"backend/domain/services/{service_name}",
            "transformation": "class_to_service",
            "notes": "Transform BLE manager to service (CRITICAL: Functional component)",
            "priority": "high"
        }
    
    # BLE Routes/Endpoints
    elif "routes/api" in file_path_lower and ("ble" in filename_lower or "bluetooth" in filename_lower):
        endpoint_name = filename_lower.replace("_routes.py", ".py")
        return {
            "phase": "phase1",
            "category": "endpoints",
            "destination": f"backend/api/endpoints/{endpoint_name}",
            "transformation": "router_refactor",
            "notes": "Refactor BLE routes to endpoints (CRITICAL: Functional component)",
            "priority": "high"
        }
    
    # UI Components
    elif "routes/ui" in file_path_lower or "/ui/" in file_path_lower:
        return {
            "phase": "phase1",
            "category": "endpoints",
            "destination": f"backend/api/endpoints/ui_{os.path.basename(file_path)}",
            "transformation": "direct_move",
            "notes": "UI-related component (CRITICAL: Functional component)",
            "priority": "high"
        }
    
    # WebSocket Components
    elif any(ws_term in file_path_lower for ws_term in ["/ws/", "websocket", "socket"]):
        return {
            "phase": "phase1",
            "category": "websockets",
            "destination": f"backend/api/websockets/{os.path.basename(file_path)}",
            "transformation": "websocket_adapter",
            "notes": "WebSocket component (CRITICAL for real-time communication)",
            "priority": "high"
        }
    
    # Phase 2: Core business logic
    
    # Other Manager Classes
    elif "_manager" in filename_lower:
        service_name = filename_lower.replace("_manager.py", "_service.py")
        return {
            "phase": "phase2",
            "category": "services",
            "destination": f"backend/domain/services/{service_name}",
            "transformation": "class_to_service",
            "notes": "Transform manager to service pattern"
        }
    
    # Other API Routes
    elif "routes/api" in file_path_lower:
        if filename_lower.endswith("_routes.py"):
            endpoint_name = filename_lower.replace("_routes.py", ".py")
        else:
            endpoint_name = filename_lower
            
        return {
            "phase": "phase2",
            "category": "endpoints",
            "destination": f"backend/api/endpoints/{endpoint_name}",
            "transformation": "router_refactor",
            "notes": "Refactor API routes to use service pattern"
        }
    
    # Models
    elif "model" in filename_lower or "schema" in filename_lower:
        return {
            "phase": "phase2",
            "category": "models",
            "destination": f"backend/domain/models/{os.path.basename(file_path)}",
            "transformation": "model_update",
            "notes": "Update model with proper imports and organization"
        }
    
    # Phase 3: Supporting components
    
    # Security Components
    elif "security" in file_path_lower or "auth" in filename_lower or "jwt" in filename_lower:
        return {
            "phase": "phase3",
            "category": "security",
            "destination": f"backend/infrastructure/security/{os.path.basename(file_path)}",
            "transformation": "security_adapter",
            "notes": "Adapt security component to new architecture"
        }
    
    # Configuration Files
    elif "config" in filename_lower or "settings" in filename_lower:
        return {
            "phase": "phase3",
            "category": "config",
            "destination": f"backend/core/config/{os.path.basename(file_path)}",
            "transformation": "direct_move",
            "notes": "Move configuration file to dedicated config directory"
        }
    
    # Utilities
    elif "util" in filename_lower or "helper" in filename_lower:
        return {
            "phase": "phase3",
            "category": "utilities",
            "destination": f"backend/utils/{os.path.basename(file_path)}",
            "transformation": "direct_move",
            "notes": "Move utility functions to dedicated utilities directory"
        }
    
    # Default case - categorize as phase 3 utility
    else:
        return {
            "phase": "phase3",
            "category": "utilities",
            "destination": f"backend/utils/{os.path.basename(file_path)}",
            "transformation": "direct_move",
            "notes": "Uncategorized file - review manually"
        }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        python_files_json = sys.argv[1]
    else:
        python_files_json = "k:\\anita\\poc\\python_files.json"
    
    output_file = "k:\\anita\\poc\\targeted_migration_plan.json"
    create_targeted_plan(python_files_json, output_file)