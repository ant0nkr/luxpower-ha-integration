import logging
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX
from .entity import ModbusBridgeEntity
from .entity_descriptions.time_types import TIME_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up time entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_prefix = hass.data[DOMAIN][entry.entry_id]['settings'].get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
    api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]
    
    entities = [
        ModbusBridgeTime(coordinator, entry, desc, entity_prefix, api_client)
        for desc in TIME_TYPES
    ]
    async_add_entities(entities)

class ModbusBridgeTime(ModbusBridgeEntity, TimeEntity):
    """Represents a time entity that reads and writes a time value to a register."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):
        """Initialize the time entity."""
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)
        # Store functions for packing/unpacking the time value
        self._extract = desc["extract"]
        self._compose = desc["compose"]
        self._attr_icon = desc.get("icon")

    @property
    def native_value(self) -> dt_time | None:
        """Return the current time value."""
        register_value = self.coordinator.data.get(self._register_type, {}).get(self._register)
        if register_value is None:
            return None
        
        # Use the extract function to get hour and minute from the register value
        hour, minute = self._extract(register_value)
        
        # Validate the time to prevent Home Assistant from crashing on invalid data
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            _LOGGER.warning("Invalid time received for %s: H=%s, M=%s", self.name, hour, minute)
            return None
            
        return dt_time(hour=hour, minute=minute)

    async def async_set_value(self, value: dt_time) -> None:
        """Set the time value."""
        hour = value.hour
        minute = value.minute

        # Use the compose function to create the new register value
        new_register_value = self._compose(hour, minute)

        if not self._api_client:
            _LOGGER.error("API client not found, cannot write to time entity '%s'", self.name)
            return

        # Call the write method on the API client
        success = await self._api_client.async_write_register(self._register, new_register_value)
        
        if success:
            # Optimistically update the coordinator's data and refresh the entity
            self.coordinator.data[self._register_type][self._register] = new_register_value
            self.async_write_ha_state()