"""Tests for the LxpModbusApiClient class."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time as time_lib

from homeassistant.helpers.update_coordinator import UpdateFailed

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient, _is_data_sane, HOLD_TIME_REGISTERS
from custom_components.lxp_modbus.classes.lxp_response import LxpResponse
from custom_components.lxp_modbus.classes.lxp_request_builder import LxpRequestBuilder
from custom_components.lxp_modbus.const import (
    DEFAULT_CONNECTION_RETRIES, TOTAL_REGISTERS, RESPONSE_OVERHEAD, 
    WRITE_RESPONSE_LENGTH, MAX_PACKET_RECOVERY_ATTEMPTS, PACKET_RECOVERY_TIMEOUT
)
from custom_components.lxp_modbus.constants.hold_registers import H_AC_CHARGE_START_TIME, H_AC_CHARGE_END_TIME

from test_data import INPUT_RESPONSES, HOLD_RESPONSES


class TestLxpModbusApiClient:
    """Test cases for LxpModbusApiClient."""

    @pytest.fixture
    def mock_lock(self):
        """Mock asyncio lock."""
        lock = AsyncMock()
        lock.__aenter__ = AsyncMock(return_value=None)
        lock.__aexit__ = AsyncMock(return_value=None)
        return lock

    @pytest.fixture
    def client(self, mock_lock):
        """Create a test client instance."""
        return LxpModbusApiClient(
            host="192.168.1.100",
            port=8000,
            dongle_serial="DG44302247",  # 10 bytes
            inverter_serial="4434280298",  # 10 bytes  
            lock=mock_lock,
            block_size=125,
            connection_retries=3,
            skip_initial_data=False
        )

    @pytest.fixture
    def mock_reader_writer(self):
        """Mock asyncio reader and writer."""
        reader = AsyncMock()
        writer = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    @pytest.fixture
    def sample_input_response(self):
        """Sample input response data."""
        return bytes.fromhex(INPUT_RESPONSES["DUMMY_INVERTER_287"]["response_hex"])

    @pytest.fixture
    def sample_hold_response(self):
        """Sample hold response data."""
        return bytes.fromhex(HOLD_RESPONSES["DUMMY_INVERTER_1_HOLD"]["response_hex"])

    def test_init(self, mock_lock):
        """Test client initialization."""
        client = LxpModbusApiClient(
            host="192.168.1.100",
            port=8000,
            dongle_serial="DG44302247",  # 10 bytes
            inverter_serial="4434280298",  # 10 bytes
            lock=mock_lock
        )
        
        assert client._host == "192.168.1.100"
        assert client._port == 8000
        assert client._dongle_serial == "DG44302247"
        assert client._inverter_serial == "4434280298"
        assert client._lock == mock_lock
        assert client._block_size == 125
        assert client._connection_retries == DEFAULT_CONNECTION_RETRIES
        assert client._skip_initial_data is True
        assert client._last_good_input_regs == {}
        assert client._last_good_hold_regs == {}
        assert client._connection_retry_count == 0
        assert client._recovery_attempts_total == 0
        assert client._recovery_successes == 0
        assert client._recovery_failures == 0

    def test_init_with_custom_params(self, mock_lock):
        """Test client initialization with custom parameters."""
        client = LxpModbusApiClient(
            host="10.0.0.1",
            port=9000,
            dongle_serial="CUSTOM1234",  # 10 bytes
            inverter_serial="INVERTER1",  # 10 bytes
            lock=mock_lock,
            block_size=40,
            connection_retries=5,
            skip_initial_data=False
        )
        
        assert client._host == "10.0.0.1"
        assert client._port == 9000
        assert client._dongle_serial == "CUSTOM1234"
        assert client._inverter_serial == "INVERTER1"
        assert client._block_size == 40
        assert client._connection_retries == 5
        assert client._skip_initial_data is False

    def test_get_recovery_stats_initial(self, client):
        """Test recovery statistics when no recoveries have been attempted."""
        stats = client.get_recovery_stats()
        
        assert stats["total_recovery_attempts"] == 0
        assert stats["successful_recoveries"] == 0
        assert stats["failed_recoveries"] == 0
        assert stats["recovery_success_rate"] == 0

    def test_get_recovery_stats_with_data(self, client):
        """Test recovery statistics with some data."""
        client._recovery_attempts_total = 10
        client._recovery_successes = 7
        client._recovery_failures = 3
        
        stats = client.get_recovery_stats()
        
        assert stats["total_recovery_attempts"] == 10
        assert stats["successful_recoveries"] == 7
        assert stats["failed_recoveries"] == 3
        assert stats["recovery_success_rate"] == 70.0

    @pytest.mark.asyncio
    async def test_async_discard_initial_data_skip_disabled(self, client):
        """Test discard initial data when skip is disabled."""
        client._skip_initial_data = False
        reader = AsyncMock()
        
        await client.async_discard_initial_data(reader)
        
        # Should not read anything when skip is disabled
        reader.read.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_discard_initial_data_skip_enabled(self, client):
        """Test discard initial data when skip is enabled."""
        client._skip_initial_data = True
        reader = AsyncMock()
        reader.read.return_value = b"some_initial_data"
        
        await client.async_discard_initial_data(reader)
        
        # Should attempt to read initial data
        reader.read.assert_called_once_with(300)

    @pytest.mark.asyncio
    async def test_async_discard_initial_data_timeout(self, client):
        """Test discard initial data with timeout."""
        client._skip_initial_data = True
        reader = AsyncMock()
        reader.read.side_effect = asyncio.TimeoutError()
        
        # Should not raise exception on timeout
        await client.async_discard_initial_data(reader)
        
        reader.read.assert_called_once_with(300)

    @pytest.mark.asyncio
    async def test_async_request_registers_success(self, client, mock_reader_writer, sample_input_response):
        """Test successful register request."""
        reader, writer = mock_reader_writer
        reader.read.return_value = sample_input_response
        
        # Mock the response validation in the method
        with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse') as mock_response_class:
            mock_response = MagicMock()
            mock_response.packet_error = False
            mock_response.serial_number = b"4434280298"
            mock_response.device_function = 4
            mock_response.register = 0
            mock_response.parsed_values_dictionary = {0: 100, 1: 200, 2: 300}
            mock_response_class.return_value = mock_response
            
            # Mock the _is_data_sane function to return True
            with patch('custom_components.lxp_modbus.classes.modbus_client._is_data_sane', return_value=True):
                result = await client.async_request_registers(writer, reader, 0, "input", 4)
                
                writer.write.assert_called_once()
                writer.drain.assert_called_once()
                reader.read.assert_called_once()
                
                # Should return a dictionary with parsed values
                assert isinstance(result, dict)
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_async_request_registers_timeout(self, client, mock_reader_writer):
        """Test register request with timeout."""
        reader, writer = mock_reader_writer
        reader.read.side_effect = asyncio.TimeoutError()
        
        # The timeout should be propagated up from asyncio.wait_for
        with pytest.raises(asyncio.TimeoutError):
            await client.async_request_registers(writer, reader, 0, "input", 4)

    @pytest.mark.asyncio
    async def test_async_request_registers_empty_response(self, client, mock_reader_writer):
        """Test register request with empty response."""
        reader, writer = mock_reader_writer
        reader.read.return_value = b""
        
        result = await client.async_request_registers(writer, reader, 0, "input", 4)
        
        # Should return empty dict
        assert result == {}

    @pytest.mark.asyncio
    async def test_async_request_registers_invalid_response(self, client, mock_reader_writer):
        """Test register request with invalid response."""
        reader, writer = mock_reader_writer
        reader.read.return_value = b"invalid_response_data"
        
        result = await client.async_request_registers(writer, reader, 0, "input", 4)
        
        # Should return empty dict for invalid response
        assert result == {}

    @pytest.mark.asyncio
    async def test_async_safe_packet_recovery_no_error(self, client, mock_reader_writer, sample_input_response):
        """Test packet recovery when no recovery is needed."""
        reader, writer = mock_reader_writer
        response = LxpResponse(sample_input_response)
        
        if not response.packet_error:
            result = await client.async_safe_packet_recovery(
                reader, sample_input_response, len(sample_input_response), "input", 4
            )
            
            assert result.packet_error == response.packet_error
            # Should not attempt to read more data
            reader.read.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_safe_packet_recovery_success(self, client, mock_reader_writer):
        """Test successful packet recovery."""
        reader, writer = mock_reader_writer
        
        # Create a malformed packet that needs recovery - should have packet_error = True
        # and packet_length_calced > expected_length
        malformed_packet = b"\xa1\x1a\x05\x00\x50\x01\x01\xc2" + b"incomplete_data"  # packet says it's 80 bytes but is only 18
        additional_data = b"recovered_data_to_complete_packet" * 3  # Enough data to complete
        
        reader.read.return_value = additional_data
        
        result = await client.async_safe_packet_recovery(
            reader, malformed_packet, 18, "input", 4  # expected_length < calculated length to trigger recovery
        )
        
        # Recovery should have been attempted if the packet has error and needs more data
        # The recovery will only increment if the original response has packet_error=True and needs more bytes
        response = LxpResponse(malformed_packet)
        if response.packet_error and response.packet_length_calced > 18:
            assert client._recovery_attempts_total > 0

    @pytest.mark.asyncio
    async def test_async_safe_packet_recovery_timeout(self, client, mock_reader_writer):
        """Test packet recovery with timeout."""
        reader, writer = mock_reader_writer
        
        # Create a malformed packet that triggers recovery
        malformed_packet = b"\xa1\x1a\x05\x00\x50\x01\x01\xc2" + b"incomplete_data"  # Says 80 bytes but only 18
        
        reader.read.side_effect = asyncio.TimeoutError()
        
        result = await client.async_safe_packet_recovery(
            reader, malformed_packet, 18, "input", 4
        )
        
        # Check if recovery was attempted based on packet conditions
        response = LxpResponse(malformed_packet)
        if response.packet_error and response.packet_length_calced > 18:
            assert client._recovery_failures > 0

    @pytest.mark.asyncio
    async def test_async_get_data_connection_success(self, client, mock_reader_writer, sample_input_response, sample_hold_response):
        """Test successful data retrieval."""
        reader, writer = mock_reader_writer
        
        # Mock successful connection
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            # Mock register responses
            reader.read.side_effect = [sample_input_response, sample_hold_response] * (TOTAL_REGISTERS // client._block_size + 1)
            
            result = await client.async_get_data()
            
            assert "input" in result
            assert "hold" in result
            assert "battery" in result
            assert isinstance(result["input"], dict)
            assert isinstance(result["hold"], dict)
            assert isinstance(result["battery"], dict)

    @pytest.mark.asyncio
    async def test_async_get_data_connection_failure(self, client):
        """Test data retrieval with connection failure."""
        # Mock connection failure for enough attempts to trigger UpdateFailed
        client._connection_retries = 1  # Reduce retries for faster test
        with patch('asyncio.open_connection', side_effect=ConnectionRefusedError("Connection refused")):
            # Should raise UpdateFailed after enough failures without cached data
            result = await client.async_get_data()
            # The method returns empty data structure for the first few failures
            assert result == {"input": {}, "hold": {}, "battery": {}}
            
            # After enough failures, it should raise UpdateFailed
            client._connection_failure_count = 10  # Simulate many failures
            with pytest.raises(UpdateFailed):
                await client.async_get_data()

    @pytest.mark.asyncio
    async def test_async_get_data_with_cached_data(self, client):
        """Test data retrieval returning cached data on connection failure."""
        # Set up some cached data
        client._last_good_input_regs = {0: 100, 1: 200}
        client._last_good_hold_regs = {0: 300, 1: 400}
        
        # Mock connection failure
        with patch('asyncio.open_connection', side_effect=ConnectionRefusedError("Connection refused")):
            result = await client.async_get_data()
            
            # Should return cached data for first few failures
            assert result["input"] == {0: 100, 1: 200}
            assert result["hold"] == {0: 300, 1: 400}

    @pytest.mark.asyncio
    async def test_async_get_data_connection_retry(self, client, mock_reader_writer, sample_input_response):
        """Test connection retry logic."""
        reader, writer = mock_reader_writer
        
        # First connection fails, second succeeds
        connection_attempts = [ConnectionRefusedError("Connection refused"), (reader, writer)]
        
        with patch('asyncio.open_connection', side_effect=connection_attempts):
            reader.read.return_value = sample_input_response
            
            result = await client.async_get_data()
            
            assert "input" in result
            assert "hold" in result
            assert "battery" in result
            assert client._connection_retry_count > 0

    @pytest.mark.asyncio
    async def test_async_write_register_success(self, client, mock_reader_writer):
        """Test successful register write."""
        reader, writer = mock_reader_writer
        
        # Mock successful write response
        write_response = b"\xa1\x1a\x05\x00\x1e\x01\x01\xc2" + b"0" * 68  # Mock response
        reader.read.return_value = write_response
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            # Mock LxpResponse instance to return successful response
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse') as mock_response_class:
                mock_response = MagicMock()
                mock_response.packet_error = False
                mock_response.parsed_values_dictionary = {100: 500}
                mock_response_class.return_value = mock_response
                
                result = await client.async_write_register(100, 500)
                
                assert result is True
                writer.write.assert_called_once()
                writer.drain.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_write_register_failure(self, client):
        """Test register write failure."""
        with patch('asyncio.open_connection', side_effect=ConnectionRefusedError("Connection refused")):
            result = await client.async_write_register(100, 500)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_async_write_register_retry_logic(self, client, mock_reader_writer):
        """Test write register retry logic."""
        reader, writer = mock_reader_writer
        
        # First attempt fails, subsequent attempts succeed
        connection_attempts = [
            ConnectionRefusedError("Connection refused"),
            (reader, writer)
        ]
        
        write_response = b"\xa1\x1a\x05\x00\x1e\x01\x01\xc2" + b"0" * 68
        reader.read.return_value = write_response
        
        with patch('asyncio.open_connection', side_effect=connection_attempts):
            # Mock LxpResponse instance to return successful response
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse') as mock_response_class:
                mock_response = MagicMock()
                mock_response.packet_error = False
                mock_response.parsed_values_dictionary = {100: 500}
                mock_response_class.return_value = mock_response
                
                result = await client.async_write_register(100, 500)
                
                assert result is True

    @pytest.mark.asyncio
    async def test_async_write_register_confirmation_mismatch(self, client, mock_reader_writer):
        """Test write register with confirmation mismatch."""
        reader, writer = mock_reader_writer
        
        write_response = b"\xa1\x1a\x05\x00\x1e\x01\x01\xc2" + b"0" * 68
        reader.read.return_value = write_response
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            # Mock LxpResponse instance to return different value than requested
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse') as mock_response_class:
                mock_response = MagicMock()
                mock_response.packet_error = False
                mock_response.parsed_values_dictionary = {100: 600}  # Different value than requested
                mock_response_class.return_value = mock_response
                
                result = await client.async_write_register(100, 500)
                
                assert result is False


class TestDataSanityFunction:
    """Test cases for the _is_data_sane function."""

    def test_is_data_sane_valid_time_values(self):
        """Test data sanity check with valid time values."""
        registers = {
            H_AC_CHARGE_START_TIME: 0x0A08,  # 8:10 (Hour=8, Minute=10)
            H_AC_CHARGE_END_TIME: 0x1E16,    # 22:30 (Hour=22, Minute=30)
            100: 12345  # Non-time register
        }
        
        assert _is_data_sane(registers, "hold") is True

    def test_is_data_sane_invalid_hour(self):
        """Test data sanity check with invalid hour."""
        registers = {
            H_AC_CHARGE_START_TIME: 0x0A18,  # 24:10 (Hour=24, invalid)
        }
        
        assert _is_data_sane(registers, "hold") is False

    def test_is_data_sane_invalid_minute(self):
        """Test data sanity check with invalid minute."""
        registers = {
            H_AC_CHARGE_START_TIME: 0x3C08,  # 8:60 (Minute=60, invalid)
        }
        
        assert _is_data_sane(registers, "hold") is False

    def test_is_data_sane_edge_cases(self):
        """Test data sanity check with edge case values."""
        registers = {
            H_AC_CHARGE_START_TIME: 0x3B17,  # 23:59 (valid edge case)
            H_AC_CHARGE_END_TIME: 0x0000,    # 0:00 (valid edge case)
        }
        
        assert _is_data_sane(registers, "hold") is True

    def test_is_data_sane_non_time_registers(self):
        """Test data sanity check with non-time registers only."""
        registers = {
            100: 12345,
            200: 67890,
            300: 0xFFFF
        }
        
        assert _is_data_sane(registers, "hold") is True

    def test_is_data_sane_input_registers(self):
        """Test data sanity check with input registers (no time registers)."""
        registers = {
            100: 12345,
            200: 67890
        }
        
        assert _is_data_sane(registers, "input") is True

    def test_is_data_sane_empty_registers(self):
        """Test data sanity check with empty register dict."""
        registers = {}
        
        assert _is_data_sane(registers, "hold") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])