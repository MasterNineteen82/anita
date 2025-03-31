"""
BLE metrics collector module.

This module provides functionality for collecting and retrieving
performance metrics for BLE operations.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Set
from collections import deque
import threading

logger = logging.getLogger(__name__)

class BleMetricsCollector:
    """
    Collector for BLE operation metrics.
    
    This class tracks various performance metrics:
    - Operation counts
    - Operation timings
    - Error counts
    - Connection statistics
    """
    
    # [Full implementation as provided earlier]
    
# Singleton instance
_metrics_collector = None

def get_metrics_collector() -> BleMetricsCollector:
    """
    Get the singleton metrics collector instance.
    
    Returns:
        BleMetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = BleMetricsCollector()
    return _metrics_collector

def get_ble_metrics() -> BleMetricsCollector:
    """
    Alias for get_metrics_collector for backward compatibility.
    
    Returns:
        BleMetricsCollector instance
    """
    return get_metrics_collector()