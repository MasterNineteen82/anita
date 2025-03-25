import os
import json
import shutil
import argparse
from pathlib import Path
from dry_run import DryRunLogger

class MigrationExecutor:
    """Executes the migration plan with transformations."""
    
    def __init__(self, plan_file: str, dry_run: bool = True, logger: DryRunLogger = None):
        self.plan_file = plan_file
        self.dry_run = dry_run
        self.logger = logger or DryRunLogger(verbose=True)
        self.plan = self.load_plan()
        self.transformers = {
            "class_to_service": self.transform_manager_to_service,
            "router_refactor": self.transform_router_to_endpoint,
            "websocket_adapter": self.transform_websocket,
            "model_update": self.transform_model,
            "security_adapter": self.transform_security,
            "direct_move": self.direct_move
        }
        
    def load_plan(self):
        """Load the migration plan from the file."""
        with open(self.plan_file, 'r') as f:
            return json.load(f)
    
    def execute(self):
        """Execute the migration plan."""
        print(f"{'DRY RUN: ' if self.dry_run else ''}Executing migration plan from {self.plan_file}")
        
        # Process each category
        categories = ["services", "models", "endpoints", "websockets", 
                     "repositories", "utilities", "security", "config", 
                     "external", "database"]
        
        total_files = 0
        skipped_files = 0
        
        for category in categories:
            files = self.plan.get(category, [])
            for file_info in files:
                source = file_info["source"]
                destination = file_info["destination"]
                transformation = file_info["transformation"]
                
                # Skip manual review files
                if destination == "MANUAL_REVIEW_NEEDED":
                    if self.dry_run:
                        self.logger.log_action("SKIP", f"Skipping file requiring manual review: {source}")
                    else:
                        print(f"Skipping file requiring manual review: {source}")
                    skipped_files += 1
                    continue
                
                # Execute the appropriate transformation
                if transformation in self.transformers:
                    self.transformers[transformation](source, destination, file_info)
                    total_files += 1
                else:
                    if self.dry_run:
                        self.logger.log_action("ERROR", f"Unknown transformation '{transformation}' for {source}")
                    else:
                        print(f"ERROR: Unknown transformation '{transformation}' for {source}")
        
        if self.dry_run:
            self.logger.save_log()
            print(f"Dry run completed. {total_files} files would be processed, {skipped_files} files skipped.")
        else:
            print(f"Migration completed. {total_files} files processed, {skipped_files} files skipped.")
    
    def direct_move(self, source, destination, file_info):
        """Directly move a file without transformation."""
        if self.dry_run:
            self.logger.would_move_file(source, destination)
            return
        
        # Create the destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Copy the file
        shutil.copy2(source, destination)
        print(f"Copied {source} to {destination}")
    
    def transform_manager_to_service(self, source, destination, file_info):
        """Transform a manager class to a service."""
        if self.dry_run:
            self.logger.would_modify_file(source, "Transform manager class to service pattern")
            self.logger.would_create_file(destination, "# Service class transformed from manager")
            return
        
        # Create the destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Read the source file
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple transformation: replace classmethod with instance method
        transformed = content.replace("@classmethod", "")
        transformed = transformed.replace("cls,", "self,")
        transformed = transformed.replace("cls.", "self.")
        
        # Find the class name
        if "_manager" in source.lower():
            old_class_name = os.path.basename(source).replace(".py", "").title().replace("_", "")
            new_class_name = old_class_name.replace("Manager", "Service")
            transformed = transformed.replace(old_class_name, new_class_name)
        
        # Add dependency injection
        if "class " in transformed:
            # Add imports
            transformed = "from typing import Optional\n" + transformed
            
            # Add constructor with DI
            constructor = """
    def __init__(self, repository=None, logger=None):
        self.repository = repository
        self.logger = logger
"""
            transformed = transformed.replace("class ", "class ", 1).replace(":\n", ":\n" + constructor)
        
        # Write the transformed file
        with open(destination, 'w', encoding='utf-8') as f:
            f.write(transformed)
        
        print(f"Transformed {source} -> {destination}")
    
    def transform_router_to_endpoint(self, source, destination, file_info):
        """Transform a router file to an endpoint."""
        if self.dry_run:
            self.logger.would_modify_file(source, "Transform router to endpoint with dependency injection")
            self.logger.would_create_file(destination, "# Endpoint transformed from router")
            return
        
        # Create the destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Read the source file
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine related service name
        base_name = os.path.basename(destination).replace(".py", "")
        service_name = f"{base_name}_service"
        
        # Add imports and dependency injection
        di_imports = f"""from fastapi import Depends
from backend.core.dependencies import get_{service_name}
from backend.domain.services.{service_name} import {base_name.title()}Service
"""
        if "import " in content:
            line_end = content.find("\n", content.find("import "))
            transformed = content[:line_end+1] + "\n" + di_imports + content[line_end+1:]
        else:
            transformed = di_imports + content
        
        # Replace direct manager calls with service calls via DI
        transformed = transformed.replace(f"{base_name.title()}Manager.", f"{base_name}_service.")
        transformed = transformed.replace(f"async def ", f"async def ", 1)
        
        # Add dependencies to route functions
        transformed = transformed.replace("async def ", f"async def ", 1)
        transformed = transformed.replace(")", f", {service_name}: {base_name.title()}Service = Depends(get_{service_name}))")
        
        # Write the transformed file
        with open(destination, 'w', encoding='utf-8') as f:
            f.write(transformed)
        
        print(f"Transformed {source} -> {destination}")
    
    def transform_websocket(self, source, destination, file_info):
        """Transform a WebSocket handler."""
        # This is a simplified transformation - in reality would need more specific handling
        self.direct_move(source, destination, file_info)
    
    def transform_model(self, source, destination, file_info):
        """Transform a model file."""
        # This is a simplified transformation - in reality would need more specific handling
        self.direct_move(source, destination, file_info)
    
    def transform_security(self, source, destination, file_info):
        """Transform a security component."""
        # This is a simplified transformation - in reality would need more specific handling
        self.direct_move(source, destination, file_info)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute the migration plan")
    parser.add_argument("plan_file", help="Path to the migration plan JSON file")
    parser.add_argument("--execute", action="store_true", help="Actually execute the migration (not dry run)")
    
    args = parser.parse_args()
    
    logger = DryRunLogger(verbose=True)
    executor = MigrationExecutor(args.plan_file, dry_run=not args.execute, logger=logger)
    executor.execute()