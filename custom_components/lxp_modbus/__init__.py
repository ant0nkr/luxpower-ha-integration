"""The LuxPower Modbus Integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

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
    CONF_BATTERY_ENTITIES,
    DEFAULT_READ_ONLY,
    DEFAULT_REGISTER_BLOCK_SIZE,
    DEFAULT_CONNECTION_RETRIES,
    DEFAULT_BATTERY_ENTITIES,
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

    # Determine if battery data should be requested
    battery_entities = entry.data.get(CONF_BATTERY_ENTITIES, DEFAULT_BATTERY_ENTITIES).replace(" ", "").split(",")
    request_battery_data = bool(battery_entities) and 'none' not in battery_entities
    # Explicit serials mean the user asserts those packs exist, so the battery block
    # keeps being polled every cycle even if it stays empty.
    battery_serials_configured = any(
        value not in ('', 'none', 'auto') for value in battery_entities
    )

    # Create a single asyncio.Lock to prevent read/write race conditions
    lock = asyncio.Lock()
    block_size = entry.data.get(CONF_REGISTER_BLOCK_SIZE, DEFAULT_REGISTER_BLOCK_SIZE)
    connection_retries = entry.data.get(CONF_CONNECTION_RETRIES, DEFAULT_CONNECTION_RETRIES)
    api_client = LxpModbusApiClient(
        host, port, dongle_serial, inverter_serial, lock, block_size, connection_retries,
        request_battery_data=request_battery_data,
        battery_serials_configured=battery_serials_configured,
    )

    # Create our custom coordinator
    coordinator = LxpModbusDataUpdateCoordinator(
        hass,
        entry,
        api_client,
        poll_interval,
    )

    # Store the coordinator and other shared objects in hass.data for this entry.
    # write_lock serialises read-modify-write cycles so two entities sharing one
    # register (e.g. the eight controls packed into H_FUNCTION_ENABLE_1) cannot
    # compose their new value from the same pre-write snapshot.
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "settings": {**entry.data, **entry.options},
        "lock": lock,
        "write_lock": asyncio.Lock(),
        "api_client": api_client
    }

    # Perform the first data refresh. Failures raise ConfigEntryNotReady, which lets
    # Home Assistant retry setup with its own backoff — do not swallow it.
    await coordinator.async_config_entry_first_refresh()

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

    # Only safe once every platform has registered its entities, and only when all
    # platforms were loaded: read-only mode skips the writable platforms, so a group
    # made up solely of switches/numbers/selects would look empty and be pruned.
    if not is_read_only:
        _async_prune_empty_devices(hass, entry)

    return True


@callback
def _async_prune_empty_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop sub-devices left behind when a device_group is renamed or removed.

    Entities move to the new sub-device, but the old one stays registered against
    this entry forever and shows up in the UI with zero entities.
    """
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    main_device_id = (DOMAIN, entry.entry_id)

    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if main_device_id in device.identifiers:
            continue  # Never touch the parent inverter device.
        # Disabled entities still belong to their group, so they must count here.
        if er.async_entries_for_device(ent_reg, device.id, include_disabled_entities=True):
            continue
        _LOGGER.debug("Removing empty sub-device '%s'", device.name)
        dev_reg.async_remove_device(device.id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Let the user delete a sub-device from the UI once it has no entities left."""
    ent_reg = er.async_get(hass)
    return not er.async_entries_for_device(
        ent_reg, device.id, include_disabled_entities=True
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Get the list of platforms that were actually loaded
    loaded_platforms = hass.data[DOMAIN][entry.entry_id].get("platforms", PLATFORMS)

    # Unload only those platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, loaded_platforms)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
