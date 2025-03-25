import os
import argparse
from pathlib import Path
from dry_run import DryRunLogger

class DirectorySetup:
    """Creates the recommended directory structure for the backend."""
    
    def __init__(self, base_dir: str = "backend", dry_run: bool = True, logger: DryRunLogger = None):
        self.base_dir = base_dir
        self.dry_run = dry_run
        self.logger = logger or DryRunLogger(verbose=True)
        
        # Define the directory structure
        self.directories = [
            # API Layer
            "api/endpoints",
            "api/websockets",
            "api/middleware",
            
            # Core Layer
            "core/config",
            "core/exceptions",
            
            # Domain Layer
            "domain/models",
            "domain/services",
            
            # Infrastructure Layer
            "infrastructure/database",
            "infrastructure/external",
            "infrastructure/repositories",
            "infrastructure/security",
            
            # Utils
            "utils",
            
            # Tests
            "../tests/api",
            "../tests/domain",
            "../tests/infrastructure",
            "../tests/core",
        ]
    
    def setup(self):
        """Create the directory structure."""
        print(f"{'DRY RUN: ' if self.dry_run else ''}Setting up directory structure in {self.base_dir}")
        
        for directory in self.directories:
            full_path = os.path.normpath(os.path.join(self.base_dir, directory))
            init_file = os.path.join(full_path, "__init__.py")
            
            if self.dry_run:
                self.logger.would_create_directory(full_path)
                self.logger.would_create_file(init_file, "# Auto-generated __init__.py file")
            else:
                os.makedirs(full_path, exist_ok=True)
                print(f"Created directory: {full_path}")
                
                # Create __init__.py file
                if not os.path.exists(init_file):
                    with open(init_file, 'w') as f:
                        f.write("# Auto-generated __init__.py file")
                    print(f"Created file: {init_file}")
        
        # Special handling for root __init__.py
        root_init = os.path.join(self.base_dir, "__init__.py")
        if self.dry_run:
            self.logger.would_create_file(root_init, "# ANITA Backend Package")
        else:
            with open(root_init, 'w') as f:
                f.write("# ANITA Backend Package")
            print(f"Created file: {root_init}")
        
        if self.dry_run:
            self.logger.save_log()
        else:
            print("Directory structure setup complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup the directory structure for the backend")
    parser.add_argument("--base-dir", default="backend", help="Base directory for the backend")
    parser.add_argument("--execute", action="store_true", help="Actually create the directories (not dry run)")
    parser.add_argument("--log-file", help="Path to save the dry run log file")
    
    args = parser.parse_args()
    
    logger = DryRunLogger(log_file=args.log_file, verbose=True)
    setup = DirectorySetup(base_dir=args.base_dir, dry_run=not args.execute, logger=logger)
    setup.setup()