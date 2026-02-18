"""Tests for the LxpModbusDataUpdateCoordinator class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from homeassistant.helpers.update_coordinator import UpdateFailed

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.coordinator import (
    LxpModbusDataUpdateCoordinator,
    RECOVERY_MODE_THRESHOLD,
    RECOVERY_INTERVAL_INITIAL,
    RECOVERY_INTERVAL_MEDIUM,
    RECOVERY_INTERVAL_HIGH,
    RECOVERY_ESCALATION_MEDIUM,
    RECOVERY_ESCALATION_HIGH,
)


class TestLxpModbusDataUpdateCoordinator:
    """Test cases for LxpModbusDataUpdateCoordinator."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        hass.data = {}
        # The DataUpdateCoordinator uses hass.loop internally via async helpers,
        # so we provide a mock bus and loop to prevent AttributeErrors.
        hass.bus = MagicMock()
        return hass

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client with async_get_data."""
        client = AsyncMock()
        client.async_get_data = AsyncMock(return_value={"input": {0: 100}, "hold": {0: 200}})
        return client

    @pytest.fixture
    def coordinator(self, mock_hass, mock_api_client):
        """Create a coordinator instance with mocked dependencies."""
        with patch(
            "custom_components.lxp_modbus.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ):
            coord = LxpModbusDataUpdateCoordinator(
                hass=mock_hass,
                api_client=mock_api_client,
                poll_interval=30,
                entry_title="Test Inverter",
            )
            # After patching __init__, the parent won't set these attributes,
            # so we set the ones the coordinator methods rely on.
            coord.hass = mock_hass
            coord.update_interval = timedelta(seconds=30)
            coord.async_refresh = MagicMock()
            return coord

    # ---------------------------------------------------------------
    # 1. Initialization - correct attributes
    # ---------------------------------------------------------------
    def test_init_correct_attributes(self, coordinator, mock_api_client):
        """Test that the coordinator initializes with correct default attributes."""
        assert coordinator.api_client is mock_api_client
        assert coordinator._failed_updates == 0
        assert coordinator._last_success is None
        assert coordinator._is_recovering is False
        assert coordinator._recovery_interval is None
        assert coordinator._original_poll_interval == 30

    # ---------------------------------------------------------------
    # 2. _async_update_data - success resets failed_updates
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_update_data_success_resets_failed_updates(self, coordinator):
        """Test that a successful update resets the failed_updates counter."""
        coordinator._failed_updates = 5

        data = await coordinator._async_update_data()

        assert coordinator._failed_updates == 0
        assert data == {"input": {0: 100}, "hold": {0: 200}}

    # ---------------------------------------------------------------
    # 3. _async_update_data - success exits recovery mode
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_update_data_success_exits_recovery_mode(self, coordinator):
        """Test that a successful update exits recovery mode and restores normal interval."""
        cancel_callback = MagicMock()
        coordinator._is_recovering = True
        coordinator._recovery_interval = cancel_callback

        data = await coordinator._async_update_data()

        assert coordinator._is_recovering is False
        assert coordinator._recovery_interval is None
        cancel_callback.assert_called_once()
        assert coordinator.update_interval == timedelta(seconds=30)
        assert data == {"input": {0: 100}, "hold": {0: 200}}

    # ---------------------------------------------------------------
    # 4. _async_update_data - UpdateFailed increments counter
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_update_data_update_failed_increments_counter(self, coordinator):
        """Test that an UpdateFailed exception increments the failed_updates counter."""
        coordinator.api_client.async_get_data.side_effect = UpdateFailed("connection lost")
        coordinator._failed_updates = 0

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._failed_updates == 1

    # ---------------------------------------------------------------
    # 5. _start_recovery_mode - sets is_recovering flag
    # ---------------------------------------------------------------
    def test_start_recovery_mode_sets_is_recovering_flag(self, coordinator):
        """Test that _start_recovery_mode sets the is_recovering flag to True."""
        coordinator._failed_updates = RECOVERY_MODE_THRESHOLD

        with patch(
            "custom_components.lxp_modbus.coordinator.async_track_time_interval",
            return_value=MagicMock(),
        ):
            coordinator._start_recovery_mode()

        assert coordinator._is_recovering is True

    # ---------------------------------------------------------------
    # 6. _start_recovery_mode - initial interval is RECOVERY_INTERVAL_INITIAL (15s)
    # ---------------------------------------------------------------
    def test_start_recovery_mode_initial_interval(self, coordinator):
        """Test that _start_recovery_mode uses RECOVERY_INTERVAL_INITIAL when failures are low."""
        coordinator._failed_updates = RECOVERY_MODE_THRESHOLD  # 3 failures, below escalation thresholds

        with patch(
            "custom_components.lxp_modbus.coordinator.async_track_time_interval",
            return_value=MagicMock(),
        ) as mock_track:
            coordinator._start_recovery_mode()

        assert coordinator.update_interval == timedelta(seconds=RECOVERY_INTERVAL_INITIAL)
        # Verify that async_track_time_interval was called with the initial interval
        mock_track.assert_called_once()
        call_args = mock_track.call_args
        assert call_args[0][2] == timedelta(seconds=RECOVERY_INTERVAL_INITIAL)

    # ---------------------------------------------------------------
    # 7. _start_recovery_mode - medium escalation at >10 failures
    # ---------------------------------------------------------------
    def test_start_recovery_mode_medium_escalation(self, coordinator):
        """Test that recovery interval escalates to RECOVERY_INTERVAL_MEDIUM at >10 failures."""
        coordinator._failed_updates = RECOVERY_ESCALATION_MEDIUM + 1  # 11 failures

        with patch(
            "custom_components.lxp_modbus.coordinator.async_track_time_interval",
            return_value=MagicMock(),
        ) as mock_track:
            coordinator._start_recovery_mode()

        assert coordinator.update_interval == timedelta(seconds=RECOVERY_INTERVAL_MEDIUM)
        call_args = mock_track.call_args
        assert call_args[0][2] == timedelta(seconds=RECOVERY_INTERVAL_MEDIUM)

    # ---------------------------------------------------------------
    # 8. _start_recovery_mode - high escalation at >20 failures
    # ---------------------------------------------------------------
    def test_start_recovery_mode_high_escalation(self, coordinator):
        """Test that recovery interval escalates to RECOVERY_INTERVAL_HIGH at >20 failures."""
        coordinator._failed_updates = RECOVERY_ESCALATION_HIGH + 1  # 21 failures

        with patch(
            "custom_components.lxp_modbus.coordinator.async_track_time_interval",
            return_value=MagicMock(),
        ) as mock_track:
            coordinator._start_recovery_mode()

        assert coordinator.update_interval == timedelta(seconds=RECOVERY_INTERVAL_HIGH)
        call_args = mock_track.call_args
        assert call_args[0][2] == timedelta(seconds=RECOVERY_INTERVAL_HIGH)

    # ---------------------------------------------------------------
    # 9. _start_recovery_mode - doesn't restart if already recovering
    # ---------------------------------------------------------------
    def test_start_recovery_mode_no_restart_if_already_recovering(self, coordinator):
        """Test that _start_recovery_mode is a no-op when already in recovery mode."""
        coordinator._is_recovering = True
        original_interval = coordinator.update_interval

        with patch(
            "custom_components.lxp_modbus.coordinator.async_track_time_interval",
            return_value=MagicMock(),
        ) as mock_track:
            coordinator._start_recovery_mode()

        # async_track_time_interval should not have been called
        mock_track.assert_not_called()
        # The update interval should remain unchanged
        assert coordinator.update_interval == original_interval

    # ---------------------------------------------------------------
    # 10. Recovery mode threshold triggers at RECOVERY_MODE_THRESHOLD (3) failures
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_recovery_mode_triggers_at_threshold(self, coordinator):
        """Test that recovery mode is triggered exactly at RECOVERY_MODE_THRESHOLD consecutive failures."""
        coordinator.api_client.async_get_data.side_effect = UpdateFailed("connection lost")

        with patch(
            "custom_components.lxp_modbus.coordinator.async_track_time_interval",
            return_value=MagicMock(),
        ):
            # Fail (RECOVERY_MODE_THRESHOLD - 1) times -- recovery should NOT trigger yet
            for i in range(RECOVERY_MODE_THRESHOLD - 1):
                with pytest.raises(UpdateFailed):
                    await coordinator._async_update_data()

            assert coordinator._failed_updates == RECOVERY_MODE_THRESHOLD - 1
            assert coordinator._is_recovering is False

            # One more failure should cross the threshold and trigger recovery
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

            assert coordinator._failed_updates == RECOVERY_MODE_THRESHOLD
            assert coordinator._is_recovering is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
