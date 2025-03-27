"""Test BLE error recovery functionality."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.modules.ble.ble_recovery import BleErrorRecovery
from bleak.exc import BleakError

@pytest.fixture
def ble_recovery():
    """Create a BleErrorRecovery instance for testing."""
    return BleErrorRecovery(logger=MagicMock())

@pytest.mark.asyncio
async def test_basic_recovery(ble_recovery):
    """Test basic connection recovery."""
    # Create a mock connection function that succeeds on the second attempt
    conn_func = AsyncMock()
    conn_func.side_effect = [False, True]
    
    # Attempt recovery
    result = await ble_recovery.recover_connection(
        "00:11:22:33:44:55",
        conn_func,
        max_attempts=3,
        backoff_factor=0.1
    )
    
    # Verify recovery succeeded after two attempts
    assert result is True
    assert conn_func.call_count == 2
    assert ble_recovery.recovery_attempts == 1
    assert ble_recovery.successful_recoveries == 1

@pytest.mark.asyncio
async def test_max_attempts_exceeded(ble_recovery):
    """Test recovery when max attempts is exceeded."""
    # Create a mock connection function that always fails
    conn_func = AsyncMock(return_value=False)
    
    # Attempt recovery with limited attempts
    result = await ble_recovery.recover_connection(
        "00:11:22:33:44:55",
        conn_func,
        max_attempts=3,
        backoff_factor=0.1
    )
    
    # Verify recovery failed after three attempts
    assert result is False
    assert conn_func.call_count == 3
    assert ble_recovery.recovery_attempts == 1
    assert ble_recovery.successful_recoveries == 0

@pytest.mark.asyncio
async def test_recovery_with_exceptions(ble_recovery):
    """Test recovery when the connection function raises exceptions."""
    # Create a mock connection function that raises exceptions
    conn_func = AsyncMock()
    conn_func.side_effect = [
        BleakError("Connection error"),
        BleakError("Device not found"),
        True
    ]
    
    # Attempt recovery
    result = await ble_recovery.recover_connection(
        "00:11:22:33:44:55",
        conn_func,
        max_attempts=5,
        backoff_factor=0.1
    )
    
    # Verify recovery succeeded after three attempts
    assert result is True
    assert conn_func.call_count == 3
    assert ble_recovery.recovery_attempts == 1
    assert ble_recovery.successful_recoveries == 1

@pytest.mark.asyncio
async def test_recovery_backoff(ble_recovery):
    """Test recovery backoff functionality."""
    # Mock time.sleep to track delays
    with patch('asyncio.sleep') as mock_sleep:
        # Create a mock connection function that succeeds after several attempts
        conn_func = AsyncMock()
        conn_func.side_effect = [False, False, False, True]
        
        # Attempt recovery with backoff
        result = await ble_recovery.recover_connection(
            "00:11:22:33:44:55",
            conn_func,
            max_attempts=5,
            backoff_factor=2.0
        )
        
        # Verify recovery succeeded
        assert result is True
        assert conn_func.call_count == 4
        
        # Verify backoff delays (should be 0, 2.0, 4.0 seconds)
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == 0
        assert mock_sleep.call_args_list[1][0][0] == 2.0
        assert mock_sleep.call_args_list[2][0][0] == 4.0

@pytest.mark.asyncio
async def test_adapter_recovery(ble_recovery):
    """Test BLE adapter recovery."""
    # Mock adapter operations
    with patch('backend.modules.ble.ble_recovery.BleakScanner') as MockScanner:
        mock_scanner = AsyncMock()
        mock_scanner.start = AsyncMock()
        mock_scanner.stop = AsyncMock()
        MockScanner.return_value = mock_scanner
        
        # Test adapter restart
        result = await ble_recovery.recover_adapter()
        
        # Verify scanner operations were called
        assert result is True
        mock_scanner.start.assert_called_once()
        mock_scanner.stop.assert_called_once()

@pytest.mark.asyncio
async def test_device_reconnection(ble_recovery):
    """Test device reconnection recovery."""
    # Mock BleakClient
    with patch('backend.modules.ble.ble_recovery.BleakClient') as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()
        MockClient.return_value = mock_client
        
        # Test reconnection
        result = await ble_recovery.reconnect_device("00:11:22:33:44:55")
        
        # Verify client operations
        assert result is True
        mock_client.connect.assert_called_once()
        mock_client.disconnect.assert_called_once()