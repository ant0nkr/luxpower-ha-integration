import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import *
from .entity import ModbusBridgeEntity
from .entity_descriptions.number_types import NUMBER_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up number entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entity_prefix = hass.data[DOMAIN][entry.entry_id]['settings'].get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX)
    api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]
    
    entities = [
        ModbusBridgeNumber(coordinator, entry, desc, entity_prefix, api_client)
        for desc in NUMBER_TYPES
    ]
    async_add_entities(entities)

class ModbusBridgeNumber(ModbusBridgeEntity, NumberEntity):
    """Represents a number entity that reads and writes a register value."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, desc: dict, entity_prefix: str, api_client):
        """Initialize the number entity."""
        super().__init__(coordinator, entry, desc, entity_prefix, api_client)
        
        # Set number-specific attributes from the description
        self._attr_native_min_value = desc["min"]
        self._attr_native_max_value = desc["max"]
        self._attr_native_step = desc.get("step", 1)
        self._attr_native_unit_of_measurement = desc.get("unit")
        self._attr_icon = desc.get("icon")
        
        # Store the multiplier for scaling
        self._multiplier = desc.get("multiplier", 1)

    @property
    def native_value(self) -> float | None:
        """Return the current value of the number entity."""
        register_value = self.coordinator.data.get(self._register_type, {}).get(self._register)
        if register_value is None:
            return None
            
        # Scale the raw register value for display in the UI
        scaled_value = register_value / self._multiplier
        
        # Return a clean int if it's a whole number, otherwise a float
        return int(scaled_value) if scaled_value == int(scaled_value) else scaled_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Scale the UI value up to the raw integer value for writing to the register
        value_to_write = int(value * self._multiplier)

        if not self._api_client:
            _LOGGER.error("API client not found, cannot write to number '%s'", self.name)
            return

        # Call the write method on the API client
        success = await self._api_client.async_write_register(self._register, value_to_write)
        
        if success:
            # Optimistically update the coordinator's data and refresh the entity
            self.coordinator.data[self._register_type][self._register] = value_to_write
            self.async_write_ha_state()