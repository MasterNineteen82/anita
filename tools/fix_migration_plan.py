import json
import os
import sys
import shutil
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"migration_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def backup_plan(migration_plan_file):
    """Create a backup of the original migration plan."""
    try:
        backup_file = f"{migration_plan_file}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(migration_plan_file, backup_file)
        logger.info(f"Backup created at: {backup_file}")
        return backup_file
    except Exception as e:
        logger.warning(f"Failed to create backup: {str(e)}")
        return None

def fix_route_mappings(migration_plan_file):
    """Fix API route mappings in the migration plan with enhanced error handling."""
    # Backup the original plan
    backup_plan(migration_plan_file)
    
    # Load the migration plan
    try:
        with open(migration_plan_file, 'r') as f:
            plan = json.load(f)
        logger.info(f"Successfully loaded migration plan from {migration_plan_file}")
    except FileNotFoundError:
        logger.error(f"Migration plan file not found: {migration_plan_file}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in migration plan file: {migration_plan_file}")
        return None
    except Exception as e:
        logger.error(f"Error loading migration plan: {str(e)}")
        return None
    
    # Initialize statistics
    stats = {
        "original_manual_review": sum(1 for cat in ["services", "models", "endpoints", "websockets", 
                                                   "repositories", "utilities", "security", 
                                                   "config", "external", "database"]
                                     if cat in plan
                                     for item in plan[cat] 
                                     if item.get("destination") == "MANUAL_REVIEW_NEEDED"),
        "endpoints_updated": 0,
        "websockets_identified": 0,
        "websockets_moved": 0,
        "frontend_components": 0,
        "bluetooth_components": 0
    }
    
    # Ensure all required categories exist
    for category in ["endpoints", "websockets", "utilities", "services"]:
        if category not in plan:
            plan[category] = []
            logger.warning(f"Created missing category in plan: {category}")
    
    # Ensure summary exists
    if "summary" not in plan:
        plan["summary"] = {}
        logger.warning("Created missing summary section in plan")
    
    # Process endpoints that need manual review
    logger.info("Processing API endpoints...")
    updated_endpoints = []
    
    # Add debug output at the start of the endpoint processing section
    logger.info("Processing endpoints section...")

    # Add a print statement for each file being processed
    for endpoint in plan["endpoints"]:
        source_path = endpoint.get("source", "")
        logger.info(f"Processing endpoint: {source_path}")
        # Add the rest of the code

    try:
        for endpoint in plan["endpoints"]:
            source_path = endpoint.get("source", "")
            filename = os.path.basename(source_path)
            
            # Skip non-route files
            if not "routes/api" in source_path:
                updated_endpoints.append(endpoint)
                continue
                
            # Handle _routes.py pattern
            if filename.endswith("_routes.py"):
                base_name = filename.replace("_routes.py", "")
                endpoint["destination"] = f"backend/api/endpoints/{base_name}.py"
                endpoint["transformation"] = "router_refactor"
                endpoint["notes"] = f"Refactor {base_name} routes to use services via dependency injection"
                stats["endpoints_updated"] += 1
                
                # Special handling for Bluetooth routes
                if "ble" in base_name.lower() or "bluetooth" in base_name.lower():
                    endpoint["priority"] = "high"
                    endpoint["notes"] += " (PRIORITY: Functional Bluetooth component)"
                    stats["bluetooth_components"] += 1
                    
            # Handle other API files
            elif "routes/api" in source_path:
                base_name = os.path.splitext(filename)[0]
                endpoint["destination"] = f"backend/api/endpoints/{base_name}.py"
                endpoint["transformation"] = "router_refactor"
                endpoint["notes"] = f"Refactor {base_name} endpoints to use services via dependency injection"
                stats["endpoints_updated"] += 1
                
                # Special handling for Bluetooth endpoints
                if "ble" in base_name.lower() or "bluetooth" in base_name.lower():
                    endpoint["priority"] = "high"
                    endpoint["notes"] += " (PRIORITY: Functional Bluetooth component)"
                    stats["bluetooth_components"] += 1
            else:
                # Keep other files marked for manual review
                logger.debug(f"Keeping file for manual review: {source_path}")
                
            updated_endpoints.append(endpoint)
        
        plan["endpoints"] = updated_endpoints
        logger.info(f"Processed {len(updated_endpoints)} API endpoints")
        
    except Exception as e:
        logger.error(f"Error processing endpoints: {str(e)}")
    
    # Specific fix for API routes - to be added to fix_migration_plan.py
    logger.info("Fixing API route mappings...")
    for endpoint in plan["endpoints"]:
        source_path = endpoint.get("source", "")
        if "routes/api/" in source_path:
            filename = os.path.basename(source_path)
            base_name = filename.replace("_routes.py", "").lower()
            
            # Handle special case files
            if not filename.endswith("_routes.py"):
                base_name = os.path.splitext(filename)[0].lower()
                
            endpoint["destination"] = f"backend/api/endpoints/{base_name}.py"
            endpoint["transformation"] = "router_refactor"
            endpoint["notes"] = f"Refactor {base_name} routes to use services via dependency injection"
            stats["endpoints_updated"] += 1
            
            logger.info(f"Updated route: {source_path} -> {endpoint['destination']}")
    
    # Process WebSocket handlers
    logger.info("Processing WebSocket handlers...")
    try:
        # Handle websocket files in routes/websockets and routes/ui folders
        websocket_files_to_add = []
        
        # First search in utilities for files in websocket folders
        for util in plan.get("utilities", []):
            source_path = util.get("source", "")
            
            # Check if this utility is in a websocket or UI directory
            if any(ws_dir in source_path for ws_dir in ["routes/websockets", "routes/ui", "/ws/"]):
                filename = os.path.basename(source_path)
                
                # Skip __init__.py files
                if filename == "__init__.py":
                    continue
                    
                # Create a new entry for this websocket file
                ws_file = {
                    "source": source_path,
                    "destination": f"backend/api/websockets/{filename}",
                    "transformation": "websocket_adapter",
                    "notes": f"Move WebSocket handler to new architecture"
                }
                
                # Special handling for UI-related WebSockets
                if "routes/ui" in source_path:
                    ws_file["notes"] += " (UI WebSocket)"
                    ws_file["priority"] = "high"
                    stats["frontend_components"] += 1
                
                websocket_files_to_add.append(ws_file)
                stats["websockets_identified"] += 1
        
        # Add discovered websocket files to the plan
        plan["websockets"].extend(websocket_files_to_add)
        logger.info(f"Added {len(websocket_files_to_add)} WebSocket files from utilities")
        
        # Fix existing WebSocket handlers
        for ws_file in plan["websockets"]:
            source_path = ws_file.get("source", "")
            
            # Handle specific WebSocket manager files
            if "ws/manager.py" in source_path:
                ws_file["destination"] = "backend/api/websockets/ws_manager.py"
                ws_file["transformation"] = "websocket_adapter"
                ws_file["notes"] = "Convert WebSocket manager to new architecture"
                ws_file["priority"] = "high"  # WebSocket managers are critical
            
            # Handle other WebSocket files
            elif any(ws_part in source_path for ws_part in ["/ws/", "websocket", "socket"]):
                filename = os.path.basename(source_path)
                ws_file["destination"] = f"backend/api/websockets/{filename}"
                ws_file["transformation"] = "websocket_adapter"
                ws_file["notes"] = "Convert WebSocket component to new architecture"
        
        logger.info(f"Processed {len(plan['websockets'])} WebSocket files")
        
    except Exception as e:
        logger.error(f"Error processing WebSocket handlers: {str(e)}")
    
    # Process utilities that are really WebSocket or UI components
    logger.info("Moving WebSocket and UI components from utilities...")
    try:
        ws_files_to_move = []
        
        # Identify WebSocket-related files in utilities
        for util in plan.get("utilities", []):
            source_path = util.get("source", "")
            
            # Look for WebSocket-related files
            if any(ws_term in source_path.lower() for ws_term in ["ws/", "websocket", "socket", "event"]):
                filename = os.path.basename(source_path)
                
                # Update the utility to be moved to WebSockets
                util["destination"] = f"backend/api/websockets/{filename}"
                util["transformation"] = "websocket_adapter"
                util["notes"] = "Move WebSocket component to websockets directory"
                ws_files_to_move.append(util)
                stats["websockets_moved"] += 1
            
            # Special handling for UI utilities
            elif "ui" in source_path.lower() and not "/static/" in source_path:
                util["priority"] = "high"
                util["notes"] = "UI-related utility (PRIORITY: Functional UI component)"
                stats["frontend_components"] += 1
        
        # Move identified WebSocket files from utilities to websockets
        for ws_file in ws_files_to_move:
            if ws_file in plan["utilities"]:
                plan["utilities"].remove(ws_file)
                plan["websockets"].append(ws_file)
        
        logger.info(f"Moved {len(ws_files_to_move)} WebSocket files from utilities")
        
    except Exception as e:
        logger.error(f"Error moving WebSocket files: {str(e)}")
    
    # Special handling for Bluetooth services
    logger.info("Processing Bluetooth services...")
    try:
        for service in plan.get("services", []):
            source_path = service.get("source", "")
            
            # Identify Bluetooth-related services
            if any(bt_term in source_path.lower() for bt_term in ["ble", "bluetooth"]):
                service["priority"] = "high"
                service["notes"] = "Bluetooth service (PRIORITY: Functional component)"
                stats["bluetooth_components"] += 1
        
        logger.info(f"Processed Bluetooth services")
        
    except Exception as e:
        logger.error(f"Error processing Bluetooth services: {str(e)}")
    
    # Update summary stats
    try:
        # Count manual review needed files after updates
        manual_review_needed = 0
        for category in ["services", "models", "endpoints", "websockets", "repositories", 
                         "utilities", "security", "config", "external", "database"]:
            if category in plan:
                manual_review_needed += sum(1 for item in plan[category] 
                                           if item.get("destination") == "MANUAL_REVIEW_NEEDED")
        
        # Update summary statistics
        plan["summary"].update({
            "manual_review_needed": manual_review_needed,
            "endpoints_updated": stats["endpoints_updated"],
            "websockets_identified": stats["websockets_identified"],
            "websockets_moved": stats["websockets_moved"],
            "frontend_components": stats["frontend_components"],
            "bluetooth_components": stats["bluetooth_components"],
            "last_updated": datetime.now().isoformat()
        })
        
        logger.info(f"Updated summary statistics")
        
    except Exception as e:
        logger.error(f"Error updating summary statistics: {str(e)}")
    
    # Save updated plan
    try:
        updated_file = migration_plan_file.replace(".json", "_updated.json")
        with open(updated_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        logger.info(f"Updated migration plan saved to: {updated_file}")
        logger.info(f"Manual review items reduced from {stats['original_manual_review']} to {manual_review_needed}")
        logger.info(f"Identified {stats['frontend_components']} frontend components and {stats['bluetooth_components']} Bluetooth components")
        
        return updated_file
        
    except Exception as e:
        logger.error(f"Error saving updated plan: {str(e)}")
        return None

def main():
    """Main entry point with command line parsing."""
    if len(sys.argv) > 1:
        migration_plan_file = sys.argv[1]
    else:
        migration_plan_file = "k:\\anita\\poc\\migration_plan.json"
    
    logger.info(f"Starting migration plan fix for: {migration_plan_file}")
    result = fix_route_mappings(migration_plan_file)
    
    if result:
        logger.info(f"Successfully updated migration plan: {result}")
    else:
        logger.error("Failed to update migration plan")

if __name__ == "__main__":
    main()