# debug_imports.py
import sys
import os
import importlib.util
from pathlib import Path
import logging
from datetime import datetime

# Set up logging to both file and console
def setup_logging():
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f'debug_imports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging output to: {log_file}")
    return logger

def debug_imports():
    logger = setup_logging()
    logger.info("=== Import Debug Script ===")

    # Add the project root to sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(project_root)
    logger.info("Added project root to sys.path: %s", project_root)

    logger.info("\n1. Current Working Directory:")
    logger.info(os.getcwd())

    logger.info("\n2. sys.path:")
    for path in sys.path:
        logger.info(f"  - {path}")

    logger.info("\n3. Project Root (K:\\anita\\):")
    logger.info(f"  - Project root: {project_root}")
    logger.info(f"  - Exists: {os.path.exists(project_root)}")
    logger.info(f"  - In sys.path: {project_root in sys.path}")

    logger.info("\n4. backend Directory (K:\\anita\\poc\\backend\\):")
    backend_dir = os.path.join(project_root, 'poc', 'backend')  # Fix the path
    logger.info(f"  - Path: {backend_dir}")
    logger.info(f"  - Exists: {os.path.exists(backend_dir)}")

    logger.info("\n5. ws Directory (K:\\anita\\poc\\backend\\ws\\):")
    ws_dir = os.path.join(backend_dir, 'ws')
    logger.info(f"  - Path: {ws_dir}")
    logger.info(f"  - Exists: {os.path.exists(ws_dir)}")
    if os.path.exists(ws_dir):
        logger.info(f"  - Contents: {os.listdir(ws_dir)}")

    logger.info("\n6. manager.py File (K:\\anita\\poc\\backend\\ws\\manager.py):")
    manager_file = os.path.join(ws_dir, 'manager.py')
    logger.info(f"  - Path: {manager_file}")
    logger.info(f"  - Exists: {os.path.exists(manager_file)}")

    logger.info("\n7. __init__.py File (K:\\anita\\poc\\backend\\ws\\__init__.py):")
    init_file = os.path.join(ws_dir, '__init__.py')
    logger.info(f"  - Path: {init_file}")
    logger.info(f"  - Exists: {os.path.exists(init_file)}")
    if os.path.exists(init_file):
        with open(init_file, 'r', encoding='utf-8') as f:
            logger.info(f"  - Contents:\n{f.read()}")

    logger.info("\n8. Attempt to Import ws.manager:")
    try:
        from backend.ws.manager import manager  # Fix the import path
        logger.info("  - Import successful!")
        logger.info(f"  - manager: {manager}")
    except ModuleNotFoundError as e:
        logger.error(f"  - Import failed: {e}")
        logger.info("  - Possible causes:")
        logger.info("    - 'ws' directory not found in backend/")
        logger.info("    - 'manager.py' not found in ws/")
        logger.info("    - Case sensitivity issue (e.g., 'WS' instead of 'ws')")
        logger.info("    - Stale .pyc files or __pycache__ directories")
        logger.info("    - sys.path does not include the project root")

    logger.info("\n9. Check for Stale .pyc Files and __pycache__ Directories:")
    pyc_files = list(Path(project_root).rglob("*.pyc"))
    pycache_dirs = list(Path(project_root).rglob("__pycache__"))
    logger.info(f"  - .pyc files found: {len(pyc_files)}")
    for pyc in pyc_files:
        logger.info(f"    - {pyc}")
    logger.info(f"  - __pycache__ directories found: {len(pycache_dirs)}")
    for pycache in pycache_dirs:
        logger.info(f"    - {pycache}")

    logger.info("\n10. Attempt to Import Using importlib:")
    spec = importlib.util.find_spec("backend.ws.manager")
    if spec:
        logger.info("  - Module spec found!")
        logger.info(f"  - Origin: {spec.origin}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        logger.info("  - Import successful using importlib!")
    else:
        logger.info("  - Module spec not found. The 'ws' package cannot be resolved.")

if __name__ == "__main__":
    debug_imports()