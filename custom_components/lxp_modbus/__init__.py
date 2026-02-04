"""The LuxPower Modbus Integration."""
import asyncio
import logging
from datetime import timedelta
import time as time_lib

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import *
from .classes.lxp_request_builder import LxpRequestBuilder
from .classes.lxp_response import LxpResponse
from .classes.modbus_client import LxpModbusApiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the LuxPower Modbus component from a config entry."""
    # Ensure the top-level dictionary for our integration exists in hass.data
    hass.data.setdefault(DOMAIN, {})
    
    # Get configuration values from the config entry
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    dongle_serial = entry.data[CONF_DONGLE_SERIAL]
    inverter_serial = entry.data[CONF_INVERTER_SERIAL]
    poll_interval = entry.data[CONF_POLL_INTERVAL]
    battery_entities = entry.data.get(CONF_BATTERY_ENTITIES, DEFAULT_BATTERY_ENTITIES).replace(" ","").split(",")
    request_battery_data = len(battery_entities) and not 'none' in battery_entities

    # Create a single asyncio.Lock to prevent read/write race conditions
    lock = asyncio.Lock()
    block_size = entry.data.get(CONF_REGISTER_BLOCK_SIZE, DEFAULT_REGISTER_BLOCK_SIZE)
    connection_retries = entry.data.get(CONF_CONNECTION_RETRIES, DEFAULT_CONNECTION_RETRIES)
    api_client = LxpModbusApiClient(host, port, dongle_serial, inverter_serial, 
                       lock, block_size, connection_retries, request_battery_data=request_battery_data)

    # Create a custom DataUpdateCoordinator with reconnection logic
    class LxpModbusDataUpdateCoordinator(DataUpdateCoordinator):
        """Class to manage fetching LuxPower Modbus data."""

        def __init__(self, hass, api_client, poll_interval):
            """Initialize the coordinator."""
            super().__init__(
                hass,
                _LOGGER,
                name=f"{INTEGRATION_TITLE} ({entry.title})",
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
                if not self._is_recovering and self._failed_updates >= 3:
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
            
            # Switch to a more aggressive polling schedule during recovery
            # Start with 15 seconds and gradually increase if still failing
            recovery_interval = 15
            if self._failed_updates > 10:
                recovery_interval = 30
            if self._failed_updates > 20:
                recovery_interval = 60
            
            self.update_interval = timedelta(seconds=recovery_interval)
            
            # Also set up a periodic forced refresh that runs in parallel
            # to the regular update schedule
            @callback
            def periodic_recovery_refresh(now=None):
                """Force a refresh on a timer."""
                _LOGGER.debug(f"Recovery mode: forcing a refresh attempt (fail count: {self._failed_updates})")
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
    
    # Create our custom coordinator
    coordinator = LxpModbusDataUpdateCoordinator(
        hass,
        api_client,
        poll_interval
    )
    
    # Store the coordinator and other shared objects in hass.data for this entry
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "settings": {**entry.data, **entry.options},
        "lock": lock,
        "api_client": api_client
    }

    # Perform the first data refresh. This will block setup until the first poll is
    # successful. It also handles exceptions and configuration entry setup retries.
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        # If first refresh fails, log the error but continue setup
        # This allows the integration to be configured even if the inverter
        # is temporarily unavailable
        _LOGGER.error(f"Initial data refresh failed: {e}. Setup will continue, but entities may be unavailable until connection is established.")
        
        # Schedule a refresh soon to try again
        async def delayed_refresh(now=None):
            try:
                await coordinator.async_refresh()
            except Exception as refresh_err:
                _LOGGER.error(f"Delayed refresh attempt failed: {refresh_err}")
        
        # Try again in 30 seconds
        hass.loop.call_later(30, lambda: hass.async_create_task(delayed_refresh()))

    # Determine which platforms to load based on the read-only setting
    settings = hass.data[DOMAIN][entry.entry_id]["settings"]
    is_read_only = settings.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)

    platforms_to_load = []
    if is_read_only:
        # In read-only mode, we only load the sensor platform.
        # It will be responsible for creating all entities.
        _LOGGER.info("Read-only mode enabled. Loading sensor and binary_sensor platforms only.")
        platforms_to_load = [Platform.SENSOR, Platform.BINARY_SENSOR]
    else:
        # In normal mode, load all platforms.
        platforms_to_load = PLATFORMS

    hass.data[DOMAIN][entry.entry_id]["platforms"] = platforms_to_load

    # Forward the setup to all platforms (sensor, number, etc.)
    await hass.config_entries.async_forward_entry_setups(entry, platforms_to_load)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Get the list of platforms that were actually loaded
    loaded_platforms = hass.data[DOMAIN][entry.entry_id].get("platforms", PLATFORMS)
    
    # Unload only those platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, loaded_platforms)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok