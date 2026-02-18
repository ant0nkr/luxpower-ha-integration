"""DataUpdateCoordinator for the LuxPower Modbus integration."""
import logging
import time as time_lib
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import INTEGRATION_TITLE

_LOGGER = logging.getLogger(__name__)

# Recovery mode constants
RECOVERY_MODE_THRESHOLD = 3
RECOVERY_INTERVAL_INITIAL = 15
RECOVERY_INTERVAL_MEDIUM = 30
RECOVERY_INTERVAL_HIGH = 60
RECOVERY_ESCALATION_MEDIUM = 10
RECOVERY_ESCALATION_HIGH = 20


class LxpModbusDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching LuxPower Modbus data."""

    def __init__(self, hass: HomeAssistant, api_client, poll_interval: int, entry_title: str):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{INTEGRATION_TITLE} ({entry_title})",
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=poll_interval),
        )
        self.api_client = api_client
        self._failed_updates = 0
        self._last_success = None
        self._is_recovering = False
        self._recovery_interval = None
        self._original_poll_interval = poll_interval

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            data = await self.api_client.async_get_data()
            self._failed_updates = 0
            self._last_success = time_lib.time()

            # If we were in recovery mode, go back to normal
            if self._is_recovering:
                _LOGGER.info("Connection recovered! Resuming normal polling schedule.")
                self._is_recovering = False
                if self._recovery_interval:
                    self._recovery_interval()
                    self._recovery_interval = None
                # Restore normal update interval
                self.update_interval = timedelta(seconds=self._original_poll_interval)

            return data
        except UpdateFailed as err:
            self._failed_updates += 1

            # Start recovery mode if we're not already in it
            if not self._is_recovering and self._failed_updates >= RECOVERY_MODE_THRESHOLD:
                self._start_recovery_mode()

            # After several consecutive failures, we should still raise the error
            # to make sure the entities show as unavailable
            raise err

    def _start_recovery_mode(self):
        """Start a more aggressive reconnection strategy."""
        if self._is_recovering:
            return

        self._is_recovering = True
        _LOGGER.warning("Connection lost! Starting recovery mode with more frequent reconnection attempts.")

        # Switch to a more aggressive polling schedule during recovery,
        # gradually increasing the interval if still failing
        recovery_interval = RECOVERY_INTERVAL_INITIAL
        if self._failed_updates > RECOVERY_ESCALATION_MEDIUM:
            recovery_interval = RECOVERY_INTERVAL_MEDIUM
        if self._failed_updates > RECOVERY_ESCALATION_HIGH:
            recovery_interval = RECOVERY_INTERVAL_HIGH

        self.update_interval = timedelta(seconds=recovery_interval)

        # Also set up a periodic forced refresh that runs in parallel
        # to the regular update schedule
        @callback
        def periodic_recovery_refresh(now=None):
            """Force a refresh on a timer."""
            _LOGGER.debug("Recovery mode: forcing a refresh attempt (fail count: %s)", self._failed_updates)
            self.async_refresh()

        # Cancel any existing recovery interval
        if self._recovery_interval:
            self._recovery_interval()

        # Set up a recurring timer for forced refresh attempts
        self._recovery_interval = async_track_time_interval(
            self.hass,
            periodic_recovery_refresh,
            timedelta(seconds=recovery_interval)
        )
