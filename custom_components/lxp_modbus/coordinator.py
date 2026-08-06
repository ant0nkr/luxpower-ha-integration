"""DataUpdateCoordinator for the LuxPower Modbus integration."""
import logging
import time as time_lib
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api_client, poll_interval: int):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Passing the entry explicitly is required by Home Assistant; the
            # implicit ContextVar fallback is removed in 2026.8.
            config_entry=entry,
            name=f"{INTEGRATION_TITLE} ({entry.title})",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.api_client = api_client
        self._failed_updates = 0
        self._last_success = None
        self._is_recovering = False
        self._original_poll_interval = poll_interval

    @property
    def failed_updates(self) -> int:
        """Return the number of consecutive failed updates."""
        return self._failed_updates

    @property
    def is_recovering(self) -> bool:
        """Return True while the coordinator is on the accelerated retry schedule."""
        return self._is_recovering

    @property
    def last_success(self) -> float | None:
        """Return the timestamp of the last successful update."""
        return self._last_success

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            data = await self.api_client.async_get_data()
        except UpdateFailed:
            self._register_failure()
            raise
        except Exception as err:
            self._register_failure()
            raise UpdateFailed(f"Unexpected error polling the inverter: {err}") from err

        self._failed_updates = 0
        self._last_success = time_lib.time()

        # If we were in recovery mode, go back to the normal schedule
        if self._is_recovering:
            _LOGGER.info("Connection recovered! Resuming normal polling schedule.")
            self._is_recovering = False
            self.update_interval = timedelta(seconds=self._original_poll_interval)

        return data

    def _register_failure(self) -> None:
        """Count a failed update and escalate the retry schedule if needed."""
        self._failed_updates += 1

        if self._failed_updates < RECOVERY_MODE_THRESHOLD:
            return

        # Only the coordinator's own schedule is adjusted. An additional parallel
        # timer would double the request rate against a dongle that is already
        # failing, and would keep firing after the config entry is unloaded.
        recovery_interval = RECOVERY_INTERVAL_INITIAL
        if self._failed_updates > RECOVERY_ESCALATION_MEDIUM:
            recovery_interval = RECOVERY_INTERVAL_MEDIUM
        if self._failed_updates > RECOVERY_ESCALATION_HIGH:
            recovery_interval = RECOVERY_INTERVAL_HIGH

        if not self._is_recovering:
            self._is_recovering = True
            _LOGGER.warning("Connection lost! Starting recovery mode with more frequent reconnection attempts.")

        new_interval = timedelta(seconds=recovery_interval)
        if self.update_interval != new_interval:
            _LOGGER.debug("Recovery mode: polling every %ss (fail count: %s)",
                          recovery_interval, self._failed_updates)
            self.update_interval = new_interval
