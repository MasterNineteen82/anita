# filepath: k:\anita\poc\tools\targeted_migration.py
"""Create targeted migration plan focusing on critical components first."""
import json
import os

def create_targeted_plan(input_plan_file, output_plan_file):
    """Create a targeted migration plan with phases."""
    with open(input_plan_file, 'r') as f:
        full_plan = json.load(f)
    
    # Create phased plan
    phased_plan = {
        "phase1": {  # Critical functionality (UI and Bluetooth)
            "services": [],
            "endpoints": [],
            "websockets": []
        },
        "phase2": {  # Core business logic
            "services": [],
            "models": [],
            "repositories": []
        },
        "phase3": {  # Supporting components
            "utilities": [],
            "security": [],
            "config": []
        }
    }
    
    # Process services - target BLE
    for service in full_plan["services"]:
        if "ble" in service["source"].lower() or "bluetooth" in service["source"].lower():
            service["priority"] = "high"
            phased_plan["phase1"]["services"].append(service)
        else:
            phased_plan["phase2"]["services"].append(service)
    
    # Process endpoints - map routes and prioritize BLE
    for endpoint in full_plan["endpoints"]:
        source_path = endpoint["source"]
        if "routes/api/" in source_path:
            filename = os.path.basename(source_path)
            if filename.endswith("_routes.py"):
                base_name = filename.replace("_routes.py", "")
            else:
                base_name = os.path.splitext(filename)[0]
            
            endpoint["destination"] = f"backend/api/endpoints/{base_name}.py"
            endpoint["transformation"] = "router_refactor"
            
            if "ble" in base_name.lower() or "bluetooth" in base_name.lower():
                endpoint["priority"] = "high"
                phased_plan["phase1"]["endpoints"].append(endpoint)
            else:
                phased_plan["phase2"]["endpoints"].append(endpoint)
        elif "routes/ui/" in source_path:
            endpoint["priority"] = "high"
            phased_plan["phase1"]["endpoints"].append(endpoint)
        else:
            phased_plan["phase3"]["endpoints"].append(endpoint)
    
    # Save the phased plan
    with open(output_plan_file, 'w') as f:
        json.dump(phased_plan, f, indent=2)
    
    print(f"Created targeted migration plan: {output_plan_file}")
    
if __name__ == "__main__":
    create_targeted_plan("k:\\anita\\poc\\migration_plan.json", 
                        "k:\\anita\\poc\\targeted_migration_plan.json")