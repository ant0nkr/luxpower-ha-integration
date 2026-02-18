"""Tests for the ModbusConnectionManager class."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.connection_manager import (
    ModbusConnectionManager,
    CONNECTION_TIMEOUT,
    CLOSE_TIMEOUT,
    INITIAL_DATA_READ_SIZE,
    INITIAL_DATA_TIMEOUT,
)


class TestModbusConnectionManager:
    """Test cases for ModbusConnectionManager."""

    @pytest.fixture
    def manager(self):
        """Create a test connection manager instance with default skip_initial_data."""
        return ModbusConnectionManager(
            host="192.168.1.100",
            port=8000,
            connection_retries=3,
        )

    @pytest.fixture
    def manager_no_skip(self):
        """Create a test connection manager with skip_initial_data disabled."""
        return ModbusConnectionManager(
            host="192.168.1.100",
            port=8000,
            connection_retries=3,
            skip_initial_data=False,
        )

    @pytest.fixture
    def mock_reader(self):
        """Mock asyncio StreamReader."""
        return AsyncMock(spec=asyncio.StreamReader)

    @pytest.fixture
    def mock_writer(self):
        """Mock asyncio StreamWriter."""
        writer = AsyncMock(spec=asyncio.StreamWriter)
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return writer

    # --- Initialization tests ---

    def test_init(self):
        """Test connection manager initialization with default parameters."""
        manager = ModbusConnectionManager(
            host="192.168.1.100",
            port=8000,
            connection_retries=3,
        )

        assert manager.host == "192.168.1.100"
        assert manager.port == 8000
        assert manager.connection_retries == 3
        assert manager._skip_initial_data is True

    def test_init_with_custom_params(self):
        """Test connection manager initialization with custom parameters."""
        manager = ModbusConnectionManager(
            host="10.0.0.1",
            port=9000,
            connection_retries=5,
            skip_initial_data=False,
        )

        assert manager.host == "10.0.0.1"
        assert manager.port == 9000
        assert manager.connection_retries == 5
        assert manager._skip_initial_data is False

    # --- Property tests ---

    def test_host_property(self, manager):
        """Test host property returns the configured host."""
        assert manager.host == "192.168.1.100"

    def test_port_property(self, manager):
        """Test port property returns the configured port."""
        assert manager.port == 8000

    def test_connection_retries_property(self, manager):
        """Test connection_retries property returns the configured value."""
        assert manager.connection_retries == 3

    # --- async_connect tests ---

    @pytest.mark.asyncio
    async def test_async_connect_success(self, manager):
        """Test successful TCP connection."""
        mock_reader = AsyncMock(spec=asyncio.StreamReader)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter)

        with patch('asyncio.open_connection', return_value=(mock_reader, mock_writer)) as mock_open:
            reader, writer = await manager.async_connect()

            mock_open.assert_called_once_with("192.168.1.100", 8000)
            assert reader is mock_reader
            assert writer is mock_writer

    @pytest.mark.asyncio
    async def test_async_connect_timeout(self, manager):
        """Test connection attempt that times out."""
        with patch('asyncio.open_connection', side_effect=asyncio.TimeoutError()):
            with pytest.raises(asyncio.TimeoutError):
                await manager.async_connect()

    # --- async_close tests ---

    @pytest.mark.asyncio
    async def test_async_close_success(self, manager, mock_writer):
        """Test successful connection close."""
        await manager.async_close(mock_writer)

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_close_with_none_writer(self, manager):
        """Test close with None writer returns immediately without error."""
        await manager.async_close(None)
        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_async_close_timeout(self, manager, mock_writer):
        """Test close that times out is handled gracefully."""
        mock_writer.wait_closed.side_effect = asyncio.TimeoutError()

        # Should not raise; the TimeoutError is caught and logged
        await manager.async_close(mock_writer)

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_close_connection_error(self, manager, mock_writer):
        """Test close that raises ConnectionError is handled gracefully."""
        mock_writer.wait_closed.side_effect = ConnectionError("Connection reset")

        # Should not raise; the ConnectionError is caught and logged
        await manager.async_close(mock_writer)

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    # --- async_discard_initial_data tests ---

    @pytest.mark.asyncio
    async def test_async_discard_initial_data_skip_enabled(self, manager, mock_reader):
        """Test discard initial data when skip is enabled reads data."""
        mock_reader.read.return_value = b"some_initial_data"

        with patch(
            'custom_components.lxp_modbus.classes.connection_manager.LxpResponse'
        ) as mock_response_class:
            mock_response = MagicMock()
            mock_response.info = "test_info"
            mock_response_class.return_value = mock_response

            await manager.async_discard_initial_data(mock_reader)

            mock_reader.read.assert_called_once_with(INITIAL_DATA_READ_SIZE)
            mock_response_class.assert_called_once_with(b"some_initial_data")

    @pytest.mark.asyncio
    async def test_async_discard_initial_data_skip_disabled(self, manager_no_skip, mock_reader):
        """Test discard initial data when skip is disabled is a no-op."""
        await manager_no_skip.async_discard_initial_data(mock_reader)

        mock_reader.read.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_discard_initial_data_timeout(self, manager, mock_reader):
        """Test discard initial data when timeout occurs is suppressed."""
        mock_reader.read.side_effect = asyncio.TimeoutError()

        # Should not raise; TimeoutError is suppressed
        await manager.async_discard_initial_data(mock_reader)

        mock_reader.read.assert_called_once_with(INITIAL_DATA_READ_SIZE)

    @pytest.mark.asyncio
    async def test_async_discard_initial_data_empty_response(self, manager, mock_reader):
        """Test discard initial data when dongle sends empty bytes."""
        mock_reader.read.return_value = b""

        with patch(
            'custom_components.lxp_modbus.classes.connection_manager.LxpResponse'
        ) as mock_response_class:
            await manager.async_discard_initial_data(mock_reader)

            mock_reader.read.assert_called_once_with(INITIAL_DATA_READ_SIZE)
            # LxpResponse should NOT be constructed when ignored data is empty/falsy
            mock_response_class.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
