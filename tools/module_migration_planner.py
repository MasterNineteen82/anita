import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from dry_run import DryRunLogger

class MigrationPlanner:
    """Plans the migration of modules to the new architecture."""
    
    def __init__(self, python_files_json: str, output_file: str = None, logger: DryRunLogger = None):
        self.python_files_json = python_files_json
        self.output_file = output_file or "migration_plan.json"
        self.logger = logger or DryRunLogger(verbose=True)
        self.migration_plan = {
            "services": [],
            "models": [],
            "endpoints": [],
            "websockets": [],
            "repositories": [],
            "utilities": [],
            "security": [],
            "config": [],
            "external": [],
            "database": [],
            "summary": {}
        }
    
    def load_python_files(self):
        """Load the Python files JSON data."""
        with open(self.python_files_json, 'r') as f:
            return json.load(f)
    
    def map_module_to_destination(self, file_path, file_name):
        """Map a module to its destination in the new architecture."""
        # Basic mapping based on filename patterns and directory
        name_lower = file_name.lower()
        
        # Manager classes -> domain/services
        if "_manager" in name_lower and file_path.endswith(".py"):
            base_name = os.path.basename(file_path)
            service_name = base_name.replace("_manager.py", "_service.py")
            return {
                "source": file_path,
                "destination": f"backend/domain/services/{service_name}",
                "transformation": "class_to_service",
                "notes": "Transform manager class to service pattern with repositories"
            }
        
        # Route files -> api/endpoints
        elif "routes/api" in file_path and file_name.endswith("_routes.py"):
            base_name = file_name.replace("_routes.py", "")
            return {
                "source": file_path,
                "destination": f"backend/api/endpoints/{base_name}.py",
                "transformation": "router_refactor",
                "notes": f"Refactor {base_name} routes to use services via dependency injection"
            }
        
        # WebSocket handlers -> api/websockets
        elif "websocket" in name_lower or "ws" in name_lower or "socket" in name_lower:
            base_name = os.path.basename(file_path)
            return {
                "source": file_path,
                "destination": f"backend/api/websockets/{base_name}",
                "transformation": "websocket_adapter",
                "notes": "Adapt WebSocket handler to new structure with DI"
            }
        
        # Models -> domain/models
        elif "model" in name_lower:
            base_name = os.path.basename(file_path)
            return {
                "source": file_path,
                "destination": f"backend/domain/models/{base_name}",
                "transformation": "model_update",
                "notes": "Update model imports and organization"
            }
        
        # Security-related files -> infrastructure/security
        elif "security" in name_lower or "auth" in name_lower or "jwt" in name_lower:
            base_name = os.path.basename(file_path)
            return {
                "source": file_path,
                "destination": f"backend/infrastructure/security/{base_name}",
                "transformation": "security_adapter",
                "notes": "Adapt security component to new structure"
            }
        
        # Utilities -> utils
        elif "util" in name_lower or name_lower == "utils.py":
            base_name = os.path.basename(file_path)
            return {
                "source": file_path,
                "destination": f"backend/utils/{base_name}",
                "transformation": "direct_move",
                "notes": "Move utility functions directly"
            }
        
        # Config files -> core/config
        elif "config" in name_lower or "setting" in name_lower:
            base_name = os.path.basename(file_path)
            return {
                "source": file_path,
                "destination": f"backend/core/config/{base_name}",
                "transformation": "direct_move",
                "notes": "Move configuration directly"
            }
        
        # Database files -> infrastructure/database
        elif "database" in name_lower or "db" in name_lower:
            base_name = os.path.basename(file_path)
            return {
                "source": file_path,
                "destination": f"backend/infrastructure/database/{base_name}",
                "transformation": "direct_move",
                "notes": "Move database components directly"
            }
        
        # Default case - need manual review
        else:
            return {
                "source": file_path,
                "destination": "MANUAL_REVIEW_NEEDED",
                "transformation": "manual",
                "notes": "Needs manual assessment for proper placement"
            }
    
    def categorize_file(self, mapping):
        """Categorize a file mapping into the appropriate section."""
        destination = mapping["destination"]
        
        if "/domain/services/" in destination:
            self.migration_plan["services"].append(mapping)
        elif "/domain/models/" in destination:
            self.migration_plan["models"].append(mapping)
        elif "/api/endpoints/" in destination:
            self.migration_plan["endpoints"].append(mapping)
        elif "/api/websockets/" in destination:
            self.migration_plan["websockets"].append(mapping)
        elif "/infrastructure/repositories/" in destination:
            self.migration_plan["repositories"].append(mapping)
        elif "/utils/" in destination:
            self.migration_plan["utilities"].append(mapping)
        elif "/infrastructure/security/" in destination:
            self.migration_plan["security"].append(mapping)
        elif "/core/config/" in destination:
            self.migration_plan["config"].append(mapping)
        elif "/infrastructure/external/" in destination:
            self.migration_plan["external"].append(mapping)
        elif "/infrastructure/database/" in destination:
            self.migration_plan["database"].append(mapping)
        else:
            # Handle MANUAL_REVIEW_NEEDED and other special cases
            if "transformation" in mapping and mapping["transformation"] == "manual":
                if "manager" in mapping["source"].lower():
                    self.migration_plan["services"].append(mapping)
                elif "model" in mapping["source"].lower():
                    self.migration_plan["models"].append(mapping)
                elif "route" in mapping["source"].lower():
                    self.migration_plan["endpoints"].append(mapping)
                else:
                    self.migration_plan["utilities"].append(mapping)
    
    def create_migration_plan(self):
        """Create a migration plan for all Python files."""
        python_files_data = self.load_python_files()
        
        print(f"Creating migration plan from {self.python_files_json}...")
        
        # Process only actual Python modules, not __init__.py or archived files
        skip_dirs = ['.archive', '__pycache__']
        
        file_count = 0
        
        for dir_path, files in python_files_data['directories'].items():
            # Skip archive directories
            if any(skip_dir in dir_path for skip_dir in skip_dirs):
                continue
                
            for file_info in files:
                file_name = file_info['name']
                
                # Skip __init__.py files
                if file_name == '__init__.py':
                    continue
                
                file_path = file_info['path']
                
                # Map this file to its destination
                mapping = self.map_module_to_destination(file_path, file_name)
                
                # Log the planned action
                self.logger.would_move_file(mapping["source"], mapping["destination"])
                self.logger.log_action("TRANSFORM", f"Would transform {mapping['source']} using {mapping['transformation']}")
                
                # Categorize this mapping
                self.categorize_file(mapping)
                
                file_count += 1
        
        # Generate summary
        self.migration_plan["summary"] = {
            "total_files": file_count,
            "services": len(self.migration_plan["services"]),
            "models": len(self.migration_plan["models"]),
            "endpoints": len(self.migration_plan["endpoints"]),
            "websockets": len(self.migration_plan["websockets"]),
            "repositories": len(self.migration_plan["repositories"]),
            "utilities": len(self.migration_plan["utilities"]),
            "security": len(self.migration_plan["security"]),
            "config": len(self.migration_plan["config"]),
            "external": len(self.migration_plan["external"]),
            "database": len(self.migration_plan["database"]),
            "manual_review_needed": sum(1 for s in self.migration_plan["services"] if s["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for m in self.migration_plan["models"] if m["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for e in self.migration_plan["endpoints"] if e["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for w in self.migration_plan["websockets"] if w["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for r in self.migration_plan["repositories"] if r["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for u in self.migration_plan["utilities"] if u["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for s in self.migration_plan["security"] if s["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for c in self.migration_plan["config"] if c["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for e in self.migration_plan["external"] if e["destination"] == "MANUAL_REVIEW_NEEDED") +
                                    sum(1 for d in self.migration_plan["database"] if d["destination"] == "MANUAL_REVIEW_NEEDED")
        }
        
        print(f"Migration plan created for {file_count} files.")
        print("\nSummary:")
        for category, count in self.migration_plan["summary"].items():
            print(f"  {category}: {count}")
        
        # Save the plan to a file
        with open(self.output_file, 'w') as f:
            json.dump(self.migration_plan, f, indent=2)
        
        print(f"\nMigration plan saved to: {self.output_file}")
        print("Review this file to understand how files will be migrated.")
        
        return self.migration_plan

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a migration plan for Python files")
    parser.add_argument("python_files_json", help="Path to the python_files.json file")
    parser.add_argument("--output", "-o", help="Output file for the migration plan")
    
    args = parser.parse_args()
    
    logger = DryRunLogger(verbose=True)
    planner = MigrationPlanner(args.python_files_json, args.output, logger)
    planner.create_migration_plan()