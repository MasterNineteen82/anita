"""
BLE Device Information Utilities

This module provides functions to enhance BLE device information with:
1. Manufacturer identification based on company codes
2. Device type detection based on service UUIDs
3. Human-readable service descriptions
"""

import logging
import binascii
from typing import Dict, List, Optional, Any, Tuple

# Set up logging
logger = logging.getLogger(__name__)

# Known Bluetooth SIG company identifiers (first 2 bytes of manufacturer data)
# Source: https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/
COMPANY_IDENTIFIERS = {
    0x004C: "Apple, Inc.",
    0x0006: "Microsoft",
    0x00E0: "Google",
    0x0075: "Samsung Electronics Co. Ltd.",
    0x0059: "Nordic Semiconductor ASA",
    0x0157: "Anhui Huami Information Technology Co., Ltd.",
    0x0499: "Ruuvi Innovations Ltd.",
    0x0001: "Ericsson Technology Licensing",
    0x00D7: "Polar Electro Oy",
    0x0087: "Garmin International, Inc.",
    0x0310: "Nest Labs Inc.",
    0x0046: "Sony Corporation",
    0x0078: "Nike, Inc.",
    0x0131: "Logitech International SA",
    0x001D: "Qualcomm",
    0x0002: "Intel Corporation",
    0x0154: "Tile, Inc."
    # Add more as needed
}

# Known service UUIDs with human-readable names and device category hints
# Source: https://www.bluetooth.com/specifications/gatt/services/
KNOWN_SERVICES = {
    # Standard services
    "1800": {"name": "Generic Access", "category": "Generic"},
    "1801": {"name": "Generic Attribute", "category": "Generic"},
    "1802": {"name": "Immediate Alert", "category": "Health"},
    "1803": {"name": "Link Loss", "category": "Generic"},
    "1804": {"name": "Tx Power", "category": "Generic"},
    "1805": {"name": "Current Time", "category": "Time"},
    "1806": {"name": "Reference Time Update", "category": "Time"},
    "1807": {"name": "Next DST Change", "category": "Time"},
    "1808": {"name": "Glucose", "category": "Health"},
    "1809": {"name": "Health Thermometer", "category": "Health"},
    "180A": {"name": "Device Information", "category": "Generic"},
    "180D": {"name": "Heart Rate", "category": "Health"},
    "180E": {"name": "Phone Alert Status", "category": "Phone"},
    "180F": {"name": "Battery", "category": "Power"},
    "1810": {"name": "Blood Pressure", "category": "Health"},
    "1811": {"name": "Alert Notification", "category": "Notification"},
    "1812": {"name": "Human Interface Device", "category": "HID"},
    "1813": {"name": "Scan Parameters", "category": "Generic"},
    "1814": {"name": "Running Speed and Cadence", "category": "Fitness"},
    "1815": {"name": "Automation IO", "category": "IoT"},
    "1816": {"name": "Cycling Speed and Cadence", "category": "Fitness"},
    "1818": {"name": "Cycling Power", "category": "Fitness"},
    "1819": {"name": "Location and Navigation", "category": "Location"},
    "181A": {"name": "Environmental Sensing", "category": "Environmental"},
    "181B": {"name": "Body Composition", "category": "Health"},
    "181C": {"name": "User Data", "category": "User"},
    "181D": {"name": "Weight Scale", "category": "Health"},
    "181E": {"name": "Bond Management", "category": "Generic"},
    "181F": {"name": "Continuous Glucose Monitoring", "category": "Health"},
    "1820": {"name": "Internet Protocol Support", "category": "Network"},
    "1821": {"name": "Indoor Positioning", "category": "Location"},
    "1822": {"name": "Pulse Oximeter", "category": "Health"},
    "1823": {"name": "HTTP Proxy", "category": "Network"},
    "1824": {"name": "Transport Discovery", "category": "Network"},
    "1825": {"name": "Object Transfer", "category": "Transfer"},
    "1826": {"name": "Fitness Machine", "category": "Fitness"},
    "1827": {"name": "Mesh Provisioning", "category": "Mesh"},
    "1828": {"name": "Mesh Proxy", "category": "Mesh"},
    "1829": {"name": "Reconnection Configuration", "category": "Generic"},
    # Add more as needed
}

# Device categories based on service combinations
DEVICE_CATEGORIES = {
    "Fitness Tracker": ["180D", "1814", "1816", "1826"],
    "Smartwatch": ["180D", "1809", "180A", "180F"],
    "Health Monitor": ["1809", "1808", "1810", "1822"],
    "Smart Home": ["1815", "181A", "1820", "1821"],
    "Beacon": ["1802", "180A", "180F"],
    "HID Device": ["1812", "1800", "180A"],
    "Audio Device": ["180A", "1800", "1801", "1803"]
}

def decode_manufacturer_data(manufacturer_data: Dict) -> Dict:
    """
    Decode manufacturer data to identify the company.
    
    Args:
        manufacturer_data: Dictionary with company ID as key and data as value
        
    Returns:
        Dictionary with decoded manufacturer information
    """
    result = {}
    
    for company_id_bytes, data in manufacturer_data.items():
        # Company ID is usually stored as a hex string after serialization
        try:
            # If it's already a number, use it directly
            if isinstance(company_id_bytes, int):
                company_id = company_id_bytes
            # If it's a string, try to convert it
            elif isinstance(company_id_bytes, str):
                # Remove any '0x' prefix and convert to int
                company_id = int(company_id_bytes.replace('0x', ''), 16)
            else:
                logger.warning(f"Unrecognized company ID format: {company_id_bytes}")
                continue
                
            company_name = COMPANY_IDENTIFIERS.get(company_id, f"Unknown (0x{company_id:04X})")
            
            # Process the data based on known manufacturer formats
            processed_data = {
                "company_name": company_name,
                "company_id": f"0x{company_id:04X}",
                "raw_data": data if isinstance(data, str) else binascii.hexlify(data).decode('ascii') if isinstance(data, bytes) else str(data)
            }
            
            # Apple-specific processing
            if company_id == 0x004C:
                processed_data["is_apple"] = True
                # TODO: Add specific Apple packet format decoding
            
            # Add other manufacturer-specific processing as needed
            
            result[f"0x{company_id:04X}"] = processed_data
            
        except Exception as e:
            logger.error(f"Error decoding manufacturer data: {e}")
            result[str(company_id_bytes)] = {
                "company_name": "Decoding Error",
                "raw_data": str(data)
            }
    
    return result

def identify_services(service_uuids: List[str]) -> List[Dict[str, Any]]:
    """
    Identify known services and provide human-readable descriptions.
    
    Args:
        service_uuids: List of service UUID strings
        
    Returns:
        List of dictionaries with service information
    """
    result = []
    
    for uuid in service_uuids:
        # Extract the base UUID (last 4 characters) for standard services
        base_uuid = uuid[-4:].upper() if len(uuid) >= 4 else uuid.upper()
        service_info = KNOWN_SERVICES.get(base_uuid, {"name": f"Unknown Service ({uuid})", "category": "Unknown"})
        
        result.append({
            "uuid": uuid,
            "name": service_info["name"],
            "category": service_info["category"]
        })
    
    return result

def determine_device_type(service_uuids: List[str]) -> Tuple[str, float]:
    """
    Determine the likely device type based on service UUIDs.
    
    Args:
        service_uuids: List of service UUID strings
        
    Returns:
        Tuple of (device_type, confidence) where confidence is 0.0-1.0
    """
    if not service_uuids:
        return "Unknown", 0.0
        
    # Extract the base UUIDs (last 4 characters) for standard services
    base_uuids = [uuid[-4:].upper() for uuid in service_uuids if len(uuid) >= 4]
    
    best_match = ("Generic BLE Device", 0.1)  # Default with low confidence
    
    for category, required_services in DEVICE_CATEGORIES.items():
        # Count how many of the required services are present
        matches = sum(1 for service in required_services if service in base_uuids)
        
        if matches > 0:
            # Calculate confidence based on percentage of matches and total services
            confidence = (matches / len(required_services)) * 0.7 + (matches / max(1, len(base_uuids))) * 0.3
            
            # Update if this is a better match
            if confidence > best_match[1]:
                best_match = (category, confidence)
    
    return best_match

def enhance_device_info(device: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance device information with manufacturer, service, and device type details.
    
    Args:
        device: Dictionary containing device information
        
    Returns:
        Enhanced device dictionary
    """
    try:
        # Create a deep copy to avoid modifying the original
        enhanced_device = device.copy()
        
        # Add device_type and manufacturer fields
        enhanced_device["device_type"] = "Unknown"
        enhanced_device["manufacturer"] = "Unknown"
        enhanced_device["device_class"] = "Generic"
        
        metadata = device.get("metadata", {})
        
        # Process manufacturer data if available
        if "manufacturer_data" in metadata:
            manufacturer_info = decode_manufacturer_data(metadata["manufacturer_data"])
            enhanced_device["manufacturer_info"] = manufacturer_info
            
            # Set the primary manufacturer if any were found
            if manufacturer_info:
                first_manufacturer = next(iter(manufacturer_info.values()))
                enhanced_device["manufacturer"] = first_manufacturer.get("company_name", "Unknown")
        
        # Process service UUIDs if available
        service_uuids = metadata.get("service_uuids", [])
        if service_uuids:
            enhanced_device["service_info"] = identify_services(service_uuids)
            
            # Determine device type
            device_type, confidence = determine_device_type(service_uuids)
            enhanced_device["device_type"] = device_type
            enhanced_device["type_confidence"] = confidence
            
            # Set device class based on the services
            categories = [service["category"] for service in enhanced_device.get("service_info", [])]
            if categories:
                # Use the most common category
                from collections import Counter
                most_common = Counter(categories).most_common(1)
                if most_common:
                    enhanced_device["device_class"] = most_common[0][0]
        
        # Set a friendly display name
        if device.get("name") and device.get("name") != "Unknown":
            enhanced_device["display_name"] = device.get("name")
        else:
            # Use manufacturer + device type if name is not available
            enhanced_device["display_name"] = f"{enhanced_device['manufacturer']} {enhanced_device['device_type']}"
            
        return enhanced_device
    
    except Exception as e:
        logger.error(f"Error enhancing device info: {e}")
        # Return the original device if enhancement fails
        return device
