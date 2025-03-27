"""Script to inspect BLE models and their requirements."""
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.modules.ble.ble_models import BLEDeviceInfo, ServiceInfo, CharacteristicInfo

def inspect_pydantic_model(model_class):
    """Print the fields and their types for a Pydantic model."""
    print(f"\nInspecting model: {model_class.__name__}")
    try:
        # For Pydantic v2
        if hasattr(model_class, "model_fields"):
            fields = model_class.model_fields
            for field_name, field_info in fields.items():
                required = "required" if not field_info.default_factory and field_info.default is ... else "optional"
                print(f"  - {field_name}: ({required})")
        # For Pydantic v1
        elif hasattr(model_class, "__fields__"):
            fields = model_class.__fields__
            for field_name, field_info in fields.items():
                required = "required" if field_info.required else "optional"
                print(f"  - {field_name}: ({required})")
        else:
            print("  Unable to determine model fields")
    except Exception as e:
        print(f"  Error inspecting model: {e}")

# Inspect all three models
inspect_pydantic_model(BLEDeviceInfo)
inspect_pydantic_model(ServiceInfo)
inspect_pydantic_model(CharacteristicInfo)

# Try creating instances with minimal fields
print("\n\nTrying to create model instances...\n")

try:
    device_info = BLEDeviceInfo(address="00:11:22:33:44:55", name="Test Device", rssi=-65)
    print(f"Successfully created BLEDeviceInfo: {device_info}")
except Exception as e:
    print(f"Error creating BLEDeviceInfo: {e}")

try:
    service_info = ServiceInfo(uuid="1800", description="Generic Access")
    print(f"Successfully created ServiceInfo: {service_info}")
except Exception as e:
    print(f"Error creating ServiceInfo: {e}")

try:
    char_info = CharacteristicInfo(uuid="2A00", description="Device Name")
    print(f"Successfully created CharacteristicInfo: {char_info}")
except Exception as e:
    print(f"Error creating CharacteristicInfo: {e}")