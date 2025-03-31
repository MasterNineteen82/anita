"""
BLE constants used throughout the core module.
"""

# Standard BLE UUIDs
BLE_UUID_BASE = "0000{}-0000-1000-8000-00805f9b34fb"

# Standard Services 
GENERIC_ACCESS_SERVICE = BLE_UUID_BASE.format("1800")
GENERIC_ATTRIBUTE_SERVICE = BLE_UUID_BASE.format("1801")
DEVICE_INFORMATION_SERVICE = BLE_UUID_BASE.format("180A")
BATTERY_SERVICE = BLE_UUID_BASE.format("180F")
HEART_RATE_SERVICE = BLE_UUID_BASE.format("180D")

# Standard Characteristics
DEVICE_NAME_CHAR = BLE_UUID_BASE.format("2A00")
APPEARANCE_CHAR = BLE_UUID_BASE.format("2A01")
BATTERY_LEVEL_CHAR = BLE_UUID_BASE.format("2A19")
MANUFACTURER_NAME_CHAR = BLE_UUID_BASE.format("2A29")
MODEL_NUMBER_CHAR = BLE_UUID_BASE.format("2A24")
SERIAL_NUMBER_CHAR = BLE_UUID_BASE.format("2A25")
FIRMWARE_REVISION_CHAR = BLE_UUID_BASE.format("2A26")

# Operation timeouts (seconds)
CONNECT_TIMEOUT = 10.0
DISCONNECT_TIMEOUT = 5.0
SCAN_TIMEOUT = 5.0
READ_TIMEOUT = 3.0
WRITE_TIMEOUT = 3.0

# Dictionary for easy access
BLE_CONSTANTS = {
    "service_uuids": {
        "generic_access": GENERIC_ACCESS_SERVICE,
        "generic_attribute": GENERIC_ATTRIBUTE_SERVICE,
        "device_information": DEVICE_INFORMATION_SERVICE,
        "battery": BATTERY_SERVICE,
        "heart_rate": HEART_RATE_SERVICE
    },
    "characteristic_uuids": {
        "device_name": DEVICE_NAME_CHAR,
        "appearance": APPEARANCE_CHAR,
        "battery_level": BATTERY_LEVEL_CHAR,
        "manufacturer_name": MANUFACTURER_NAME_CHAR,
        "model_number": MODEL_NUMBER_CHAR,
        "serial_number": SERIAL_NUMBER_CHAR,
        "firmware_revision": FIRMWARE_REVISION_CHAR
    },
    "timeouts": {
        "connect": CONNECT_TIMEOUT,
        "disconnect": DISCONNECT_TIMEOUT,
        "scan": SCAN_TIMEOUT,
        "read": READ_TIMEOUT,
        "write": WRITE_TIMEOUT
    }
}