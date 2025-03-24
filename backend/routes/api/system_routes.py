from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import platform
import os
import psutil
import logging
from datetime import datetime

from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors

# Define router with proper prefix and tags
router = APIRouter(tags=["system"])

# Get logger
logger = get_api_logger("system")

# Models for system information
class SystemInfo(BaseModel):
    os: str
    python_version: str
    cpu_count: int
    memory_total: int
    memory_available: int
    hostname: str
    uptime: float

class DiskInfo(BaseModel):
    device: str
    mountpoint: str
    filesystem: str
    total: int
    used: int
    free: int
    percent_used: float

# Routes for system information
@router.get("/system/info", summary="Get system information")
@handle_errors
async def get_system_info():
    """
    Get basic system information.
    
    Returns:
        Dictionary with status and system information.
    """
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = (datetime.now() - boot_time).total_seconds()
        
        system_info = {
            "os": f"{platform.system()} {platform.release()} ({platform.platform()})",
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count() or 0,
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "hostname": platform.node(),
            "uptime": uptime
        }
        
        return {
            "status": "success",
            "data": system_info
        }
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")

@router.get("/system/disk", summary="Get disk information")
@handle_errors
async def get_disk_info():
    """
    Get disk usage information.
    
    Returns:
        Dictionary with status and disk information.
    """
    try:
        disk_info = []
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent_used": usage.percent
                })
            except (PermissionError, OSError):
                # Some mountpoints may not be accessible
                pass
        
        return {
            "status": "success",
            "data": disk_info
        }
    except Exception as e:
        logger.error(f"Error getting disk info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get disk info: {str(e)}")

@router.get("/system/memory", summary="Get memory information")
@handle_errors
async def get_memory_info():
    """
    Get memory usage information.
    
    Returns:
        Dictionary with status and memory information.
    """
    try:
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()
        
        memory_info = {
            "virtual": {
                "total": virtual_memory.total,
                "available": virtual_memory.available,
                "used": virtual_memory.used,
                "free": virtual_memory.free,
                "percent_used": virtual_memory.percent
            },
            "swap": {
                "total": swap_memory.total,
                "used": swap_memory.used,
                "free": swap_memory.free,
                "percent_used": swap_memory.percent
            }
        }
        
        return {
            "status": "success",
            "data": memory_info
        }
    except Exception as e:
        logger.error(f"Error getting memory info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory info: {str(e)}")

@router.get("/system/network", summary="Get network information")
@handle_errors
async def get_network_info():
    """
    Get network interface information.
    
    Returns:
        Dictionary with status and network information.
    """
    try:
        network_info = {}
        
        # Get network interfaces info
        network_interfaces = psutil.net_if_addrs()
        for interface, addresses in network_interfaces.items():
            network_info[interface] = []
            for addr in addresses:
                address_info = {
                    "family": str(addr.family),
                    "address": addr.address
                }
                if hasattr(addr, 'netmask') and addr.netmask:
                    address_info["netmask"] = addr.netmask
                if hasattr(addr, 'broadcast') and addr.broadcast:
                    address_info["broadcast"] = addr.broadcast
                network_info[interface].append(address_info)
        
        return {
            "status": "success",
            "data": network_info
        }
    except Exception as e:
        logger.error(f"Error getting network info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get network info: {str(e)}")

@router.get("/system/processes", summary="Get running processes")
@handle_errors
async def get_processes():
    """
    Get list of running processes.
    
    Returns:
        Dictionary with status and process information.
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            # Skip processes we don't have access to
            try:
                proc_info = proc.info
                processes.append({
                    "pid": proc_info['pid'],
                    "name": proc_info['name'],
                    "username": proc_info['username'],
                    "cpu_percent": proc_info['cpu_percent'],
                    "memory_percent": proc_info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage (descending)
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        
        return {
            "status": "success",
            "data": processes[:50]  # Limit to top 50 processes
        }
    except Exception as e:
        logger.error(f"Error getting processes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get processes: {str(e)}")