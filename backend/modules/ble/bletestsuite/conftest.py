import sys
import os
import pytest

# Add the project root to the Python path for all tests
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# The correct way to configure pytest-asyncio
def pytest_configure(config):
    config.option.asyncio_mode = "strict"