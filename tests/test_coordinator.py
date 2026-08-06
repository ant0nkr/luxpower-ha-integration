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
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.title = "Test Inverter"
        entry.entry_id = "test_entry_id"
        return entry

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client with async_get_data."""
        client = AsyncMock()
        client.async_get_data = AsyncMock(return_value={"input": {0: 100}, "hold": {0: 200}})
        return client

    @pytest.fixture
    def coordinator(self, mock_hass, mock_entry, mock_api_client):
        """Create a coordinator instance with mocked dependencies."""
        with patch(
            "custom_components.lxp_modbus.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ):
            coord = LxpModbusDataUpdateCoordinator(
                hass=mock_hass,
                entry=mock_entry,
                api_client=mock_api_client,
                poll_interval=30,
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
        assert coordinator._original_poll_interval == 30

    # ---------------------------------------------------------------
    # 1b. The config entry must be forwarded to the base coordinator.
    # Home Assistant removes the implicit ContextVar fallback in 2026.8.
    # ---------------------------------------------------------------
    def test_init_passes_config_entry_to_base_coordinator(self, mock_hass, mock_entry, mock_api_client):
        """Test that config_entry is explicitly handed to DataUpdateCoordinator."""
        with patch(
            "custom_components.lxp_modbus.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ) as mock_init:
            LxpModbusDataUpdateCoordinator(
                hass=mock_hass,
                entry=mock_entry,
                api_client=mock_api_client,
                poll_interval=30,
            )

        assert mock_init.call_args.kwargs["config_entry"] is mock_entry
        assert mock_init.call_args.kwargs["update_interval"] == timedelta(seconds=30)

    # ---------------------------------------------------------------
    # 2. _async_update_data - success resets failed_updates
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_update_data_success_resets_failed_updates(self, coordinator):
        """Test that a successful update resets the failed_updates counter."""
        coordinator._failed_updates = 5

        data = await coordinator._async_update_data()

        assert coordinator._failed_updates == 0
        assert coordinator._last_success is not None
        assert data == {"input": {0: 100}, "hold": {0: 200}}

    # ---------------------------------------------------------------
    # 3. _async_update_data - success exits recovery mode
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_update_data_success_exits_recovery_mode(self, coordinator):
        """Test that a successful update exits recovery mode and restores normal interval."""
        coordinator._is_recovering = True
        coordinator.update_interval = timedelta(seconds=RECOVERY_INTERVAL_INITIAL)

        data = await coordinator._async_update_data()

        assert coordinator._is_recovering is False
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
    # 4b. Unexpected errors are reported as UpdateFailed, not leaked raw
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_async_update_data_wraps_unexpected_errors(self, coordinator):
        """Test that a non-UpdateFailed error is converted into UpdateFailed."""
        coordinator.api_client.async_get_data.side_effect = ValueError("boom")

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._failed_updates == 1

    # ---------------------------------------------------------------
    # 5. _register_failure - sets is_recovering flag at the threshold
    # ---------------------------------------------------------------
    def test_register_failure_sets_is_recovering_flag(self, coordinator):
        """Test that reaching the threshold sets the is_recovering flag to True."""
        coordinator._failed_updates = RECOVERY_MODE_THRESHOLD - 1

        coordinator._register_failure()

        assert coordinator._is_recovering is True

    # ---------------------------------------------------------------
    # 6. Recovery interval starts at RECOVERY_INTERVAL_INITIAL (15s)
    # ---------------------------------------------------------------
    def test_recovery_initial_interval(self, coordinator):
        """Test that recovery uses RECOVERY_INTERVAL_INITIAL when failures are low."""
        coordinator._failed_updates = RECOVERY_MODE_THRESHOLD - 1

        coordinator._register_failure()

        assert coordinator.update_interval == timedelta(seconds=RECOVERY_INTERVAL_INITIAL)

    # ---------------------------------------------------------------
    # 7. Medium escalation at >10 failures
    # ---------------------------------------------------------------
    def test_recovery_medium_escalation(self, coordinator):
        """Test that recovery interval escalates to RECOVERY_INTERVAL_MEDIUM at >10 failures."""
        coordinator._failed_updates = RECOVERY_ESCALATION_MEDIUM

        coordinator._register_failure()

        assert coordinator.update_interval == timedelta(seconds=RECOVERY_INTERVAL_MEDIUM)

    # ---------------------------------------------------------------
    # 8. High escalation at >20 failures
    # ---------------------------------------------------------------
    def test_recovery_high_escalation(self, coordinator):
        """Test that recovery interval escalates to RECOVERY_INTERVAL_HIGH at >20 failures."""
        coordinator._failed_updates = RECOVERY_ESCALATION_HIGH

        coordinator._register_failure()

        assert coordinator.update_interval == timedelta(seconds=RECOVERY_INTERVAL_HIGH)

    # ---------------------------------------------------------------
    # 9. Below the threshold nothing changes
    # ---------------------------------------------------------------
    def test_register_failure_below_threshold_keeps_interval(self, coordinator):
        """Test that a single failure does not change the polling schedule."""
        original_interval = coordinator.update_interval

        coordinator._register_failure()

        assert coordinator._is_recovering is False
        assert coordinator.update_interval == original_interval

    # ---------------------------------------------------------------
    # 10. Recovery mode threshold triggers at RECOVERY_MODE_THRESHOLD (3) failures
    # ---------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_recovery_mode_triggers_at_threshold(self, coordinator):
        """Test that recovery mode is triggered exactly at RECOVERY_MODE_THRESHOLD consecutive failures."""
        coordinator.api_client.async_get_data.side_effect = UpdateFailed("connection lost")

        # Fail (RECOVERY_MODE_THRESHOLD - 1) times -- recovery should NOT trigger yet
        for _ in range(RECOVERY_MODE_THRESHOLD - 1):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

        assert coordinator._failed_updates == RECOVERY_MODE_THRESHOLD - 1
        assert coordinator._is_recovering is False

        # One more failure should cross the threshold and trigger recovery
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._failed_updates == RECOVERY_MODE_THRESHOLD
        assert coordinator._is_recovering is True

    # ---------------------------------------------------------------
    # 11. No parallel refresh timer is created.
    # A second timer alongside update_interval doubled the request rate against
    # an already failing dongle and kept firing after unload.
    # ---------------------------------------------------------------
    def test_recovery_creates_no_parallel_timer(self, coordinator):
        """Test that recovery mode relies only on the coordinator's own schedule."""
        import custom_components.lxp_modbus.coordinator as coordinator_module

        assert not hasattr(coordinator_module, "async_track_time_interval")

        coordinator._failed_updates = RECOVERY_ESCALATION_HIGH
        coordinator._register_failure()

        assert not hasattr(coordinator, "_recovery_interval")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
