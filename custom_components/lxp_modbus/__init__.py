"""The LuxPower Modbus Integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_HOST,
    CONF_PORT,
    CONF_DONGLE_SERIAL,
    CONF_INVERTER_SERIAL,
    CONF_POLL_INTERVAL,
    CONF_READ_ONLY,
    CONF_REGISTER_BLOCK_SIZE,
    CONF_CONNECTION_RETRIES,
    DEFAULT_READ_ONLY,
    DEFAULT_REGISTER_BLOCK_SIZE,
    DEFAULT_CONNECTION_RETRIES,
)
from .classes.modbus_client import LxpModbusApiClient
from .coordinator import LxpModbusDataUpdateCoordinator

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

    # Create a single asyncio.Lock to prevent read/write race conditions
    lock = asyncio.Lock()
    block_size = entry.data.get(CONF_REGISTER_BLOCK_SIZE, DEFAULT_REGISTER_BLOCK_SIZE)
    connection_retries = entry.data.get(CONF_CONNECTION_RETRIES, DEFAULT_CONNECTION_RETRIES)
    api_client = LxpModbusApiClient(host, port, dongle_serial, inverter_serial, lock, block_size, connection_retries)

    # Create our custom coordinator
    coordinator = LxpModbusDataUpdateCoordinator(
        hass,
        api_client,
        poll_interval,
        entry.title
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
        _LOGGER.error("Initial data refresh failed: %s. Setup will continue, but entities may be unavailable until connection is established.", e)

        # Schedule a refresh soon to try again
        async def delayed_refresh(now=None):
            try:
                await coordinator.async_refresh()
            except Exception as refresh_err:
                _LOGGER.error("Delayed refresh attempt failed: %s", refresh_err)

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
