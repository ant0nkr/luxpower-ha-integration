import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import *
from .entity import ModbusBridgeEntity
from .entity_descriptions.binary_sensor_types import BINARY_SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up binary_sensor entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_prefix = hass.data[DOMAIN][entry.entry_id]['settings'].get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
    api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]
    
    entities = [
        ModbusBridgeBinarySensor(coordinator, entry, desc, entity_prefix, api_client)
        for desc in BINARY_SENSOR_TYPES
    ]
    async_add_entities(entities)

class ModbusBridgeBinarySensor(ModbusBridgeEntity, BinarySensorEntity):
    """Represents a binary_sensor entity that writes a value to a register."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):
        """Initialize the binary_sensor entity."""
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)
        
        self._attr_state_class = self._desc.get("state_class")
        self._attr_device_class = self._desc.get("device_class")
        self._attr_icon = desc.get("icon")

    @property
    def is_on(self):
        """Return the state of the sensor."""
        # Don't return a value until the coordinator has fetched data for the first time
        if not self.coordinator.data:
            return None

        raw_val = None
        registers = self.coordinator.data.get(self._register_type, {})
        value = registers.get(self._register)
        if value is not None:
            # Use the 'extract' lambda to parse the value (e.g., for packed bits)
            raw_val = self._desc["extract"](value)

        return raw_val
